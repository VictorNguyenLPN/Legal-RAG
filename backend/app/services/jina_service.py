import logging
import requests
from typing import List, Dict
from backend.app.config import settings

logger = logging.getLogger(__name__)


class JinaService:
    def __init__(self):
        self.api_url = "https://api.jina.ai/v1/rerank"

    def rerank(self, query: str, candidates: List[Dict], top_n: int = 5) -> List[str]:
        """
        Reranks a list of candidate document chunks using Jina AI's Multilingual Cross-Encoder API.
        """
        api_key = settings.JINA_API_KEY
        if not candidates:
            return []

        if not api_key:
            logger.warning("JINA_API_KEY is not configured. Falling back to candidate order.")
            return [c["chunk_id"] for c in candidates[:top_n]]

        # Prepare document texts for cross-encoder reranking
        documents = []
        for c in candidates:
            metadata = c.get("metadata", {})
            doc_title = metadata.get("document_title") or ""
            article = metadata.get("article_title") or metadata.get("article_number") or ""
            text = c.get("text") or ""
            combined_text = f"{doc_title} {article} {text}".strip()
            documents.append(combined_text)

        payload = {
            "model": settings.JINA_RERANK_MODEL,
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(candidates))
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                ranked_ids = [candidates[item["index"]]["chunk_id"] for item in results]
                return ranked_ids
            else:
                logger.error(f"Jina Reranker API error {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Failed to call Jina Reranker API: {e}")

        return [c["chunk_id"] for c in candidates[:top_n]]


jina_service = JinaService()
