import re
import numpy as np
from typing import List, Dict, Tuple
from rank_bm25 import BM25Okapi
from backend.app.database.vector_db import vector_db
from backend.app.config import settings

class SparseSearch:
    def __init__(self):
        self.bm25 = None
        self.chunks: List[Dict] = []
        self.initialize()

    def initialize(self) -> None:
        """
        Initializes or rebuilds the BM25 index using the current chunks in VectorDB.
        """
        self.chunks = vector_db.chunks
        if not self.chunks:
            self.bm25 = None
            return
        
        corpus_texts = [self._prepare_text(chunk) for chunk in self.chunks]
        tokenized_corpus = [self._tokenize(text) for text in corpus_texts]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def _prepare_text(self, chunk: Dict) -> str:
        """
        Formats legal metadata and text to construct a queryable document representation.
        """
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
        return "\n".join(parts)

    def _tokenize(self, text: str) -> List[str]:
        """
        Basic Vietnamese tokenization by lowercasing and splitting alphabetic characters.
        """
        text = text.lower()
        # Keep letters, numbers, and replace punctuation with spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        return text.split()

    def search(self, query: str, top_k: int = None) -> List[Tuple[Dict, float]]:
        """
        Performs BM25 search and returns list of tuples (chunk, score).
        """
        if top_k is None:
            top_k = settings.SPARSE_TOP_K

        # Auto-rebuild BM25 if VectorDB chunks changed (e.g. after calling /ingest)
        if self.bm25 is None or len(self.chunks) != len(vector_db.chunks):
            self.initialize()

        if self.bm25 is None:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        top_k = min(top_k, len(self.chunks))
        if top_k == 0:
            return []
            
        # Get top indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        return [(self.chunks[idx], float(scores[idx])) for idx in top_indices]

# Singleton instance of SparseSearch
sparse_search = SparseSearch()
