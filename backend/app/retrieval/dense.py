import numpy as np
from typing import List, Dict, Tuple
from backend.app.database.vector_db import vector_db
from backend.app.config import settings

def dense_search(query_vector: List[float], top_k: int = None) -> List[Tuple[Dict, float]]:
    """
    Performs cosine similarity search between query_vector and stored dense embeddings.
    Returns a list of tuples containing (chunk, score).
    """
    if top_k is None:
        top_k = settings.DENSE_TOP_K

    chunks, embeddings = vector_db.chunks, vector_db.embeddings
    if not chunks or embeddings is None:
        return []

    # Format arrays
    q_vec = np.array(query_vector, dtype=np.float32)
    embs = np.array(embeddings, dtype=np.float32)

    # Dot products
    dot_products = np.dot(embs, q_vec)

    # L2 Norms
    norm_embs = np.linalg.norm(embs, axis=1)
    norm_query = np.linalg.norm(q_vec)

    # Prevent division by zero
    norms = norm_embs * norm_query
    norms[norms == 0] = 1e-10

    # Cosine similarities
    similarities = dot_products / norms

    # Get sorted top_k indices descending
    top_k = min(top_k, len(chunks))
    top_indices = np.argsort(similarities)[::-1][:top_k]

    return [(chunks[idx], float(similarities[idx])) for idx in top_indices]
