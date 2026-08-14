from typing import List, Dict, Tuple
from backend.app.database.vector_db import vector_db
from backend.app.config import settings

def dense_search(query_text: str, top_k: int = None) -> List[Tuple[Dict, float]]:
    """
    Performs dense search by querying Qdrant directly.
    Returns a list of tuples containing (chunk, cosine_similarity_score).
    """
    if top_k is None:
        top_k = settings.DENSE_TOP_K
        
    return vector_db.search(query_text, top_k)
