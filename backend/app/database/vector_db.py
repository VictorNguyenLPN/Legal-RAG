import os
import json
import uuid
import logging
import warnings
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from tqdm import tqdm
# pyrefly: ignore [missing-import]
from qdrant_client import QdrantClient
# pyrefly: ignore [missing-import]
from qdrant_client.http import models
# pyrefly: ignore [missing-import]
from fastembed import SparseTextEmbedding, TextEmbedding
from backend.app.config import settings

# Suppress fastembed warnings about mean pooling / CLS embeddings changes
# warnings.filterwarnings("ignore", message=".*uses mean pooling.*")

logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self):
        # Initialize client based on config
        qdrant_url = settings.QDRANT_URL
        qdrant_api_key = settings.QDRANT_API_KEY
        
        if qdrant_url:
            logger.info(f"Connecting to Qdrant Cloud at {qdrant_url} with cloud inference enabled...")
            self.client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
                cloud_inference=True,
                timeout=120.0
            )
            self.cloud_inference = True
        else:
            # Default to local persistent storage to save embedding API costs across server restarts.
            use_memory = os.getenv("QDRANT_USE_MEMORY", "false").lower() == "true"
            if use_memory:
                logger.info("QDRANT_URL is not set. Initializing Ephemeral In-Memory Qdrant Client...")
                self.client = QdrantClient(":memory:")
            else:
                db_path = str(settings.DB_DIR / "qdrant")
                logger.info(f"QDRANT_URL is not set. Initializing Local Persistent Qdrant Client at {db_path}...")
                self.client = QdrantClient(path=db_path)
            self.cloud_inference = False
            
        self.collection_name = settings.QDRANT_COLLECTION_NAME # reuse config collection name
        
        # Initialize FastEmbed Sparse embedding model for BM25
        logger.info("Initializing FastEmbed SparseTextEmbedding (Qdrant/bm25)...")
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        
        # Initialize local dense model if not using cloud inference
        if not self.cloud_inference:
            logger.info("Initializing local FastEmbed TextEmbedding (sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)...")
            self.dense_model = TextEmbedding(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            
        # E5 Small embedding dimension is 384 (so is paraphrase-multilingual-MiniLM-L12-v2)
        self._ensure_collection(vector_size=384)

    def _ensure_collection(self, vector_size: int = 384):
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            
            if not exists:
                logger.info(f"Creating Qdrant collection: {self.collection_name} with dense vector size {vector_size}...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense": models.VectorParams(
                            size=vector_size,
                            distance=models.Distance.COSINE
                        )
                    },
                    sparse_vectors_config={
                        "sparse": models.SparseVectorParams()
                    }
                )
                logger.info(f"Successfully created collection {self.collection_name}.")
        except Exception as e:
            logger.error(f"Error ensuring Qdrant collection exists: {e}")

    def save(self, chunks: List[Dict], embeddings: Optional[np.ndarray] = None) -> None:
        """
        Saves chunks metadata, dense embeddings (generated via Cloud Inference or locally), and sparse embeddings to Qdrant.
        Generates embeddings sequentially to prevent CPU spikes, then uploads to Qdrant concurrently.
        """
        if not chunks:
            return

        self._ensure_collection(vector_size=384)

        batch_size = 128 if self.cloud_inference else 256
        total_chunks = len(chunks)
        logger.info(f"Starting ingestion of {total_chunks} chunks (batch size: {batch_size})...")

        # We can generate embeddings sequentially, and upload concurrently
        max_workers = 4
        with tqdm(total=total_chunks, desc="Ingesting to Qdrant", unit="chunk") as pbar:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for batch_start in range(0, total_chunks, batch_size):
                    batch_end = min(batch_start + batch_size, total_chunks)
                    batch_chunks = chunks[batch_start:batch_end]
                    
                    # 1. Format texts and tokenize
                    formatted_texts = []
                    texts_for_sparse = []
                    for chunk in batch_chunks:
                        metadata = chunk.get("metadata", {})
                        doc_title = metadata.get("document_title") or ""
                        hierarchy = metadata.get("hierarchy_path") or []
                        hierarchy_str = " > ".join([str(h) for h in hierarchy if h])
                        article_title = metadata.get("article_title") or ""
                        text = chunk.get("text") or ""
                        
                        parts = [
                            f"Văn bản: {doc_title}",
                            f"Vị trí cấu trúc: {hierarchy_str}",
                            f"Tiêu đề Điều: {article_title}",
                            f"Nội dung điều khoản: {text}"
                        ]
                        formatted_text = "\n".join(parts)
                        formatted_texts.append(formatted_text)
                        
                        # pyrefly: ignore [missing-import]
                        from underthesea import word_tokenize
                        tokenized_text = word_tokenize(formatted_text, format="text")
                        texts_for_sparse.append(tokenized_text)

                    # 2. Generate sparse embeddings (sequential to prevent CPU starvation)
                    sparse_embeddings = list(self.sparse_model.embed(texts_for_sparse))
                    
                    # 3. Generate local dense embeddings if fallback
                    dense_embeddings = None
                    if not self.cloud_inference:
                        dense_embeddings = list(self.dense_model.embed(formatted_texts))
                    
                    # 4. Construct PointStructs
                    points = []
                    for idx, chunk in enumerate(batch_chunks):
                        chunk_id = chunk["chunk_id"]
                        qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))
                        
                        payload = {
                            "chunk_json": json.dumps(chunk, ensure_ascii=False),
                            "text": chunk.get("text", "")
                        }
                        
                        if self.cloud_inference:
                            passage_text = f"passage: {formatted_texts[idx]}"
                            dense_vec = models.Document(
                                text=passage_text,
                                model="intfloat/multilingual-e5-small"
                            )
                        else:
                            dense_vec = dense_embeddings[idx].tolist()
                            
                        sparse_vec = sparse_embeddings[idx]
                        
                        points.append(models.PointStruct(
                            id=qdrant_id,
                            vector={
                                "dense": dense_vec,
                                "sparse": models.SparseVector(
                                    indices=sparse_vec.indices.tolist(),
                                    values=sparse_vec.values.tolist()
                                )
                            },
                            payload=payload
                        ))
                    
                    # 5. Submit the upload task to ThreadPool
                    def upload_task(points_to_upload, b_start, b_end):
                        self.client.upsert(
                            collection_name=self.collection_name,
                            points=points_to_upload
                        )
                        return b_end - b_start

                    future = executor.submit(upload_task, points, batch_start, batch_end)
                    futures.append(future)
                
                # Update progress bar as uploads complete
                for future in as_completed(futures):
                    try:
                        num_processed = future.result()
                        pbar.update(num_processed)
                    except Exception as e:
                        logger.error(f"Failed to upload batch to Qdrant: {e}")
                        
        logger.info(f"Ingestion completed for all {total_chunks} chunks.")

    def search_dense(self, query_text: str, top_k: int) -> List[Tuple[Dict, float]]:
        """
        Search using dense vector cosine similarity in Qdrant.
        """
        try:
            if self.cloud_inference:
                # E5 model requires "query: " prefix for searching
                query_obj = models.Document(
                    text=f"query: {query_text}",
                    model="intfloat/multilingual-e5-small"
                )
            else:
                # Generate embedding locally
                query_vector = list(self.dense_model.embed([query_text]))[0].tolist()
                query_obj = query_vector

            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_obj,
                using="dense",
                limit=top_k
            ).points
            
            output = []
            for hit in results:
                if hit.payload and "chunk_json" in hit.payload:
                    chunk = json.loads(hit.payload["chunk_json"])
                    output.append((chunk, hit.score))
            return output
        except Exception as e:
            logger.error(f"Error performing dense search in Qdrant: {e}")
            return []

    def search_sparse(self, query_text: str, top_k: int) -> List[Tuple[Dict, float]]:
        """
        Search using sparse vector BM25 in Qdrant.
        """
        try:
            # Tokenize query
            # pyrefly: ignore [missing-import]
            from underthesea import word_tokenize
            tokenized_query = word_tokenize(query_text, format="text")
            
            # Generate sparse vector
            query_sparse = list(self.sparse_model.embed([tokenized_query]))[0]
            
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=models.SparseVector(
                    indices=query_sparse.indices.tolist(),
                    values=query_sparse.values.tolist()
                ),
                using="sparse",
                limit=top_k
            ).points
            output = []
            for hit in results:
                if hit.payload and "chunk_json" in hit.payload:
                    chunk = json.loads(hit.payload["chunk_json"])
                    output.append((chunk, hit.score))
            return output
        except Exception as e:
            logger.error(f"Error performing sparse search in Qdrant: {e}")
            return []

    def search(self, query_text: str, top_k: int) -> List[Tuple[Dict, float]]:
        """
        Backward compatible search method mapping to search_dense.
        """
        return self.search_dense(query_text, top_k)

    @property
    def chunks(self) -> List[Dict]:
        """
        Retrieves all original chunks from Qdrant by scrolling.
        """
        try:
            if self.is_empty():
                return []
            chunks_list = []
            next_page_offset = None
            while True:
                results, next_page_offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    with_payload=True,
                    with_vectors=False,
                    offset=next_page_offset
                )
                for point in results:
                    if point.payload and "chunk_json" in point.payload:
                        chunks_list.append(json.loads(point.payload["chunk_json"]))
                if next_page_offset is None:
                    break
            return chunks_list
        except Exception as e:
            logger.error(f"Error scrolling chunks from Qdrant: {e}")
            return []

    @property
    def embeddings(self) -> Optional[np.ndarray]:
        """
        Mock embeddings property for backward compatibility with status endpoint.
        """
        if not self.is_empty():
            return np.array([1])
        return None

    def is_empty(self) -> bool:
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                return True
            return self.client.count(collection_name=self.collection_name).count == 0
        except Exception as e:
            logger.error(f"Error checking if Qdrant is empty: {e}")
            return True

    def __len__(self) -> int:
        try:
            return self.client.count(collection_name=self.collection_name).count
        except Exception as e:
            logger.error(f"Error getting Qdrant collection count: {e}")
            return 0

# Singleton instance of VectorDB
vector_db = VectorDB()
