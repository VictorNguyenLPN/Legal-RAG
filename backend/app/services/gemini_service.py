import logging
from typing import List, Optional, Tuple, Any
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types
# pyrefly: ignore [missing-import]
from google.genai.errors import APIError
from backend.app.config import settings

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        # The SDK automatically uses GEMINI_API_KEY environment variable if api_key is not passed,
        # but passing it explicitly from settings provides extra robustness and visibility.
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set. Please set it in your environment or .env file.")
        
        self.client = genai.Client(api_key=api_key) if api_key else None

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates embedding for a single text string.
        """
        if not self.client:
            raise ValueError("Gemini API Client is not initialized. Please configure GEMINI_API_KEY.")
        
        try:
            response = self.client.models.embed_content(
                model=settings.EMBEDDING_MODEL,
                contents=text,
            )
            # Safe extraction: new SDK returns a list in response.embeddings
            if response.embeddings:
                return response.embeddings[0].values
            elif hasattr(response, "embedding") and response.embedding:
                return response.embedding.values
            else:
                raise ValueError("No embedding returned in Gemini API response.")
        except APIError as e:
            logger.error(f"Error getting embedding from Gemini API: {e}")
            raise e

    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a list of text strings using parallel single-item calls.
        This avoids the BatchEmbedContents 401 authentication bug and 
        the gemini-embedding-2 multi-part aggregation issue.
        """
        from concurrent.futures import ThreadPoolExecutor
        import time

        if not self.client:
            raise ValueError("Gemini API Client is not initialized. Please configure GEMINI_API_KEY.")

        def get_single_embedding_with_retry(text: str) -> List[float]:
            max_retries = 5
            backoff = 2.0
            for retry in range(max_retries):
                try:
                    response = self.client.models.embed_content(
                        model=settings.EMBEDDING_MODEL,
                        contents=text,
                    )
                    if response.embeddings:
                        return response.embeddings[0].values
                    elif hasattr(response, "embedding") and response.embedding:
                        return response.embedding.values
                    else:
                        raise ValueError("No embedding returned in Gemini API response.")
                except APIError as e:
                    # 429 is Rate Limit / Resource Exhausted
                    if getattr(e, "code", None) == 429 or "exhausted" in str(e).lower():
                        if retry < max_retries - 1:
                            logger.warning(f"Rate limit hit. Retrying in {backoff}s... (Retry {retry + 1}/{max_retries})")
                            time.sleep(backoff)
                            backoff *= 2.0
                            continue
                    logger.error(f"Error getting single embedding: {e}")
                    raise e
            raise ValueError("Failed to retrieve embedding after maximum retries.")

        logger.info(f"Generating embeddings for {len(texts)} texts in parallel...")
        # Using 10 workers to keep it fast but avoid overwhelming the rate limits
        with ThreadPoolExecutor(max_workers=10) as executor:
            embeddings = list(executor.map(get_single_embedding_with_retry, texts))
            
        return embeddings

    def generate_answer(self, prompt: str, system_instruction: Optional[str] = None) -> Tuple[str, Optional[types.UsageMetadata]]:
        """
        Generates answer using Gemini 2.5 Flash and returns the text response and token usage metadata.
        """
        if not self.client:
            raise ValueError("Gemini API Client is not initialized. Please configure GEMINI_API_KEY.")
            
        try:
            config = types.GenerateContentConfig(
                temperature=0.0, # Highly deterministic for RAG tasks
            )
            if system_instruction:
                config.system_instruction = system_instruction

            response = self.client.models.generate_content(
                model=settings.GENERATION_MODEL,
                contents=prompt,
                config=config,
            )

            # print(response)
            usage_metadata = getattr(response, "usage_metadata", None)
            return response.text, usage_metadata
        except APIError as e:
            logger.error(f"Error generating answer from Gemini API: {e}")
            raise e

    def rerank(self, query: str, candidates: List[types.Dict], top_n: int = 5) -> List[str]:
        """
        Reranks retrieved candidate chunks using Gemini Listwise Reranking with structured output.
        Returns a list of chunk_id strings ordered by relevance.
        """
        from typing import Dict
        if not self.client:
            raise ValueError("Gemini API Client is not initialized. Please configure GEMINI_API_KEY.")
        if not candidates:
            return []

        # Prepare candidates text representation for the reranker prompt
        candidates_text_list = []
        for idx, chunk in enumerate(candidates):
            metadata = chunk.get("metadata", {})
            doc_title = metadata.get("document_title") or "N/A"
            article = metadata.get("article_title") or metadata.get("article_number") or "N/A"
            text = chunk.get("text") or ""
            candidates_text_list.append(
                f"INDEX: {idx}\n"
                f"ID: {chunk.get('chunk_id')}\n"
                f"Tài liệu: {doc_title} - Điều: {article}\n"
                f"Nội dung: {text}\n"
            )
        
        candidates_text = "\n---\n".join(candidates_text_list)
        
        prompt = (
            f"Bạn là một chuyên gia pháp lý tối ưu hóa tìm kiếm.\n"
            f"Nhiệm vụ của bạn là đánh giá và xếp hạng độ liên quan của các đoạn văn bản pháp luật dưới đây đối với Câu hỏi của người dùng.\n\n"
            f"Câu hỏi của người dùng: \"{query}\"\n\n"
            f"Danh sách các đoạn văn bản cần xếp hạng:\n"
            f"{candidates_text}\n\n"
            f"Hãy chọn ra tối đa {top_n} đoạn văn bản liên quan nhất và xếp hạng chúng theo thứ tự giảm dần của độ liên quan."
        )

        from pydantic import BaseModel, Field

        class RankedChunk(BaseModel):
            chunk_id: str = Field(description="The unique ID of the document chunk.")
            reason: str = Field(description="Brief reason in Vietnamese why this chunk is relevant to the query.")

        class RerankedList(BaseModel):
            ranked_results: List[RankedChunk] = Field(description="The list of ranked document chunks, from most relevant to least relevant.")

        try:
            config = types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=RerankedList,
            )
            response = self.client.models.generate_content(
                model=settings.GENERATION_MODEL,
                contents=prompt,
                config=config,
            )
            
            # Use response.parsed to get parsed Pydantic object
            parsed_result = response.parsed
            if parsed_result and hasattr(parsed_result, "ranked_results"):
                ranked_ids = [item.chunk_id for item in parsed_result.ranked_results]
                # Filter out any IDs that might not be in the original candidates
                valid_ids = [cid for cid in ranked_ids if any(c["chunk_id"] == cid for c in candidates)]
                logger.info(f"Gemini Reranker ranked IDs: {valid_ids}")
                return valid_ids
        except Exception as e:
            logger.error(f"Error in Gemini Listwise Reranking: {e}")
            
        # Fallback to original order if reranker fails
        return [c["chunk_id"] for c in candidates[:top_n]]

# Singleton instance of GeminiService
gemini_service = GeminiService()

