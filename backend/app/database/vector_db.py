import os
import json
import uuid
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
# pyrefly: ignore [missing-import]
from qdrant_client import QdrantClient
# pyrefly: ignore [missing-import]
from qdrant_client.http import models
# pyrefly: ignore [missing-import]
from fastembed import SparseTextEmbedding
from backend.app.config import settings

logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self):
        # Initialize client based on config
        qdrant_url = os.getenv("QDRANT_URL", "")
        qdrant_api_key = os.getenv("QDRANT_API_KEY", "")
        
        if qdrant_url:
            logger.info(f"Connecting to Qdrant Cloud at {qdrant_url}...")
            self.client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key
            )
        else:
            # Default to local persistent storage to save embedding API costs across server restarts.
            # Set QDRANT_USE_MEMORY=true in .env if purely in-memory ephemeral DB is desired.
            use_memory = os.getenv("QDRANT_USE_MEMORY", "false").lower() == "true"
            if use_memory:
                logger.info("QDRANT_URL is not set. Initializing Ephemeral In-Memory Qdrant Client...")
                self.client = QdrantClient(":memory:")
            else:
                db_path = str(settings.DB_DIR / "qdrant")
                logger.info(f"QDRANT_URL is not set. Initializing Local Persistent Qdrant Client at {db_path}...")
                self.client = QdrantClient(path=db_path)
            
        self.collection_name = settings.QDRANT_COLLECTION_NAME # reuse config collection name
        
        # Initialize FastEmbed Sparse embedding model for BM25
        logger.info("Initializing FastEmbed SparseTextEmbedding (Qdrant/bm25)...")
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        
        # Call with default 3072 dimensions for gemini-embedding-2
        self._ensure_collection(vector_size=3072)

    def _ensure_collection(self, vector_size: int = 3072):
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

    def save(self, chunks: List[Dict], embeddings: np.ndarray) -> None:
        """
        Saves chunks metadata, dense embeddings, and sparse embeddings to Qdrant.
        Using .upsert() for incremental/intelligent ingestion.
        """
        if not chunks:
            return

        embeddings_list = embeddings.tolist()
        vector_size = len(embeddings_list[0])
        
        # Re-ensure collection exists with the exact incoming vector size
        self._ensure_collection(vector_size=vector_size)

        logger.info(f"Generating sparse embeddings for {len(chunks)} chunks...")
        
        texts = []
        for chunk in chunks:
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
            
            # Apply Vietnamese tokenizer before embedding for sparse search
            # pyrefly: ignore [missing-import]
            from underthesea import word_tokenize
            tokenized_text = word_tokenize(formatted_text, format="text")
            texts.append(tokenized_text)

        # Generate sparse embeddings
        sparse_embeddings = list(self.sparse_model.embed(texts))
        
        points = []
        for idx, chunk in enumerate(chunks):
            chunk_id = chunk["chunk_id"]
            # Convert chunk_id to UUID deterministically
            qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))
            
            # Store the original chunk
            payload = {
                "chunk_json": json.dumps(chunk, ensure_ascii=False),
                "text": chunk.get("text", "")
            }
            
            # Qdrant sparse vector format
            sparse_vec = sparse_embeddings[idx]
            
            points.append(models.PointStruct(
                id=qdrant_id,
                vector={
                    "dense": embeddings_list[idx],
                    "sparse": models.SparseVector(
                        indices=sparse_vec.indices.tolist(),
                        values=sparse_vec.values.tolist()
                    )
                },
                payload=payload
            ))
            
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info(f"Successfully upserted {len(chunks)} chunks to Qdrant.")

    def search_dense(self, query_vector: List[float], top_k: int) -> List[Tuple[Dict, float]]:
        """
        Search using dense vector cosine similarity in Qdrant.
        """
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
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

    def search(self, query_vector: List[float], top_k: int) -> List[Tuple[Dict, float]]:
        """
        Backward compatible search method mapping to search_dense.
        """
        return self.search_dense(query_vector, top_k)

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
