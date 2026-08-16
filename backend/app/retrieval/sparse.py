from typing import List, Dict, Tuple
from backend.app.database.vector_db import vector_db
from backend.app.config import settings

def sparse_search(query_text: str, top_k: int = None) -> List[Tuple[Dict, float]]:
    """
    Performs BM25 search via Qdrant's sparse vector index.
    """
    if top_k is None:
        top_k = settings.SPARSE_TOP_K
    return vector_db.search_sparse(query_text, top_k)
