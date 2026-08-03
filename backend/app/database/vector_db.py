import json
import logging
import chromadb
from typing import List, Dict, Tuple, Optional
import numpy as np
from backend.app.config import settings

logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self):
        # Initialize client based on config
        if settings.CHROMA_SERVER_TYPE == "http":
            logger.info(f"Connecting to ChromaDB Server at http://{settings.CHROMA_HOST}:{settings.CHROMA_PORT}...")
            self.client = chromadb.HttpClient(
                host=settings.CHROMA_HOST,
                port=settings.CHROMA_PORT
            )
        else:
            logger.info(f"Initializing Persistent ChromaDB Client at {settings.CHROMA_PERSIST_DIR}...")
            self.client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR
            )
        
        # Get or create collection
        # Cosine distance will be calculated. Space is 'cosine'.
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def save(self, chunks: List[Dict], embeddings: np.ndarray) -> None:
        """
        Saves chunks metadata and dense embeddings to ChromaDB.
        """
        if not chunks:
            return

        # 1. Clear existing collection to perform a fresh overwrite ingestion
        try:
            existing = self.collection.get()
            if existing and existing.get("ids"):
                self.collection.delete(ids=existing["ids"])
                logger.info(f"Cleared {len(existing['ids'])} existing entries from ChromaDB collection.")
        except Exception as e:
            logger.warning(f"Failed to clear existing collection: {e}")

        # 2. Prepare metadata and documents
        ids = [chunk["chunk_id"] for chunk in chunks]
        documents = [chunk.get("text", "") for chunk in chunks]
        
        # Serialize the entire chunk dictionary to preserve original nested format
        metadatas = [{"chunk_json": json.dumps(chunk, ensure_ascii=False)} for chunk in chunks]
        embeddings_list = embeddings.tolist()

        # 3. Add to ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings_list,
            metadatas=metadatas,
            documents=documents
        )
        logger.info(f"Saved {len(chunks)} chunks & embeddings to ChromaDB collection: {settings.CHROMA_COLLECTION_NAME}.")

    def load(self) -> Tuple[List[Dict], Optional[np.ndarray]]:
        """
        Mock load method for backward compatibility.
        """
        return self.chunks, self.embeddings

    @property
    def chunks(self) -> List[Dict]:
        """
        Retrieves all original chunks from ChromaDB.
        Used primarily by SparseSearch (BM25 Okapi indexer).
        """
        try:
            results = self.collection.get()
            chunks_list = []
            if results and results.get("metadatas"):
                for meta in results["metadatas"]:
                    if meta and "chunk_json" in meta:
                        chunks_list.append(json.loads(meta["chunk_json"]))
            return chunks_list
        except Exception as e:
            logger.error(f"Error fetching chunks from ChromaDB: {e}")
            return []

    @property
    def embeddings(self) -> Optional[np.ndarray]:
        """
        Mock embeddings property for backward compatibility with status endpoint.
        Returns a mock array if ChromaDB has data, else None.
        """
        if not self.is_empty():
            # Return a simple mock to indicate embeddings exist
            return np.array([1])
        return None

    def is_empty(self) -> bool:
        """
        Checks if the ChromaDB collection is empty.
        """
        try:
            return self.collection.count() == 0
        except Exception as e:
            logger.error(f"Error checking if ChromaDB is empty: {e}")
            return True

    def __len__(self) -> int:
        """
        Returns the number of documents/chunks in the collection.
        """
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Error getting collection count: {e}")
            return 0

    def search(self, query_vector: List[float], top_k: int) -> List[Tuple[Dict, float]]:
        """
        Queries ChromaDB directly using the query vector.
        Returns a list of tuples containing (chunk, cosine_similarity_score).
        """
        if self.is_empty():
            return []

        try:
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=top_k
            )
            
            output = []
            if results and results.get("ids") and len(results["ids"]) > 0:
                ids = results["ids"][0]
                metadatas = results["metadatas"][0]
                distances = results["distances"][0]
                
                for meta, dist in zip(metadatas, distances):
                    if meta and "chunk_json" in meta:
                        chunk = json.loads(meta["chunk_json"])
                        # Cosine similarity = 1.0 - Cosine distance
                        similarity = 1.0 - float(dist)
                        output.append((chunk, similarity))
            return output
        except Exception as e:
            logger.error(f"Error performing search in ChromaDB: {e}")
            return []

# Singleton instance of VectorDB
vector_db = VectorDB()
