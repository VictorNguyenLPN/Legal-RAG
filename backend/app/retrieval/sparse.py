from typing import List, Dict, Tuple
from backend.app.database.vector_db import vector_db
from backend.app.config import settings

class SparseSearch:
    def initialize(self) -> None:
        """
        No-op initialization since indexing is handled database-side by Qdrant.
        """
        pass

    def search(self, query: str, top_k: int = None) -> List[Tuple[Dict, float]]:
        """
        Performs BM25 search via Qdrant's sparse vector index.
        """
        if top_k is None:
            top_k = settings.SPARSE_TOP_K
        return vector_db.search_sparse(query, top_k)

# Singleton instance of SparseSearch
sparse_search = SparseSearch()
