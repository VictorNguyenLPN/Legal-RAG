import json
import uuid
import logging
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
# pyrefly: ignore [missing-import]
import numpy as np
from tqdm import tqdm
# pyrefly: ignore [missing-import]
from qdrant_client import QdrantClient
# pyrefly: ignore [missing-import]
from qdrant_client.http import models
# pyrefly: ignore [missing-import]
from fastembed import SparseTextEmbedding
from backend.app.config import settings
# pyrefly: ignore [missing-import]
from underthesea import word_tokenize
logger = logging.getLogger(__name__)


class VectorDB:
    def __init__(self):
        qdrant_url = settings.QDRANT_URL
        qdrant_api_key = settings.QDRANT_API_KEY

        if not qdrant_url or not qdrant_api_key:
            raise ValueError("QDRANT_URL and QDRANT_API_KEY must be configured in environment or .env file.")

        logger.info(f"Connecting to Qdrant Cloud at {qdrant_url}")
        self.client = QdrantClient(
            url=qdrant_url,
            api_key=qdrant_api_key,
            cloud_inference=True,
            timeout=120.0
        )

        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        self._ensure_collection(vector_size=384)

    def _ensure_collection(self, vector_size: int = 384):
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
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
                logger.info(f"Created collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}")

    def save(self, chunks: List[Dict]) -> None:
        """
        Saves chunks metadata and embeddings directly to Qdrant Cloud.
        """
        if not chunks:
            return

        self._ensure_collection(vector_size=384)

        batch_size = 128
        total_chunks = len(chunks)

        with tqdm(total=total_chunks, desc="Ingesting to Qdrant Cloud", unit="chunk") as pbar:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                for batch_start in range(0, total_chunks, batch_size):
                    batch_end = min(batch_start + batch_size, total_chunks)
                    batch_chunks = chunks[batch_start:batch_end]

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
                        tokenized_text = word_tokenize(formatted_text, format="text")
                        texts_for_sparse.append(tokenized_text)

                    sparse_embeddings = list(self.sparse_model.embed(texts_for_sparse))

                    points = []
                    for idx, chunk in enumerate(batch_chunks):
                        chunk_id = chunk["chunk_id"]
                        qdrant_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))

                        payload = {
                            "chunk_json": json.dumps(chunk, ensure_ascii=False),
                            "text": chunk.get("text", "")
                        }

                        passage_text = f"passage: {formatted_texts[idx]}"
                        dense_vec = models.Document(
                            text=passage_text,
                            model="intfloat/multilingual-e5-small"
                        )
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

                    def upload_task(points_to_upload, b_start, b_end):
                        self.client.upsert(
                            collection_name=self.collection_name,
                            points=points_to_upload
                        )
                        return b_end - b_start

                    future = executor.submit(upload_task, points, batch_start, batch_end)
                    futures.append(future)

                for future in as_completed(futures):
                    try:
                        num_processed = future.result()
                        pbar.update(num_processed)
                    except Exception as e:
                        logger.error(f"Batch upload failed: {e}")

    def search_dense(self, query_text: str, top_k: int) -> List[Tuple[Dict, float]]:
        try:
            query_obj = models.Document(
                text=f"query: {query_text}",
                model="intfloat/multilingual-e5-small"
            )

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
            logger.error(f"Dense search failed: {e}")
            return []

    def search_sparse(self, query_text: str, top_k: int) -> List[Tuple[Dict, float]]:
        try:
            tokenized_query = word_tokenize(query_text, format="text")

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
            logger.error(f"Sparse search failed: {e}")
            return []

    @property
    def embeddings(self) -> Optional[np.ndarray]:
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
            logger.error(f"Failed to check database empty state: {e}")
            return True

    def __len__(self) -> int:
        try:
            return self.client.count(collection_name=self.collection_name).count
        except Exception as e:
            logger.error(f"Failed to get collection count: {e}")
            return 0


vector_db = VectorDB()
