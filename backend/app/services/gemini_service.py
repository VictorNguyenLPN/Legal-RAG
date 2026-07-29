import logging
from typing import List, Optional
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

    def get_embeddings_batch(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        """
        Generates embeddings for a list of text strings in batches.
        Includes rate limiting delay and exponential backoff retry to prevent TPM limit exhaustion.
        """
        import time
        if not self.client:
            raise ValueError("Gemini API Client is not initialized. Please configure GEMINI_API_KEY.")
        
        embeddings = []
        total_batches = (len(texts) + batch_size - 1) // batch_size
        
        for idx, i in enumerate(range(0, len(texts), batch_size)):
            batch = texts[i : i + batch_size]
            max_retries = 5
            backoff = 2.0
            
            # Simple rate limiting delay between batches
            if idx > 0:
                time.sleep(2.0)
                
            for retry in range(max_retries):
                try:
                    response = self.client.models.embed_content(
                        model=settings.EMBEDDING_MODEL,
                        contents=batch,
                    )
                    for emb in response.embeddings:
                        embeddings.append(emb.values)
                    break  # Success, exit retry loop
                except APIError as e:
                    # 429 is usually RESOURCE_EXHAUSTED
                    if getattr(e, "code", None) == 429 or "exhausted" in str(e).lower() or retry == max_retries - 1:
                        if retry < max_retries - 1:
                            logger.warning(f"Rate limit hit during batch embedding. Retrying in {backoff}s... (Retry {retry + 1}/{max_retries})")
                            time.sleep(backoff)
                            backoff *= 2.0
                            continue
                    logger.error(f"Error in batch embedding: {e}")
                    raise e
                
        return embeddings

    def generate_answer(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Generates answer using Gemini 2.5 Flash.
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
            return response.text
        except APIError as e:
            logger.error(f"Error generating answer from Gemini API: {e}")
            raise e

# Singleton instance of GeminiService
gemini_service = GeminiService()
