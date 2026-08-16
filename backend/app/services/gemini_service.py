import logging
from typing import Optional, Tuple
from google import genai
from google.genai import types
from google.genai.errors import APIError
from backend.app.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self):
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            logger.warning("GEMINI_API_KEY is not set.")
        self.client = genai.Client(api_key=api_key) if api_key else None

    def generate_answer(self, prompt: str, system_instruction: Optional[str] = None) -> Tuple[str, Optional[types.UsageMetadata]]:
        if not self.client:
            raise ValueError("Gemini API Client is not initialized.")

        try:
            config = types.GenerateContentConfig(temperature=0.0)
            if system_instruction:
                config.system_instruction = system_instruction

            chat = self.client.chats.create(model=settings.GENERATION_MODEL)
            response = chat.send_message(
                message=prompt,
                config=config,
            )
            usage_metadata = getattr(response, "usage_metadata", None)
            return response.text, usage_metadata
        except APIError as e:
            logger.error(f"Error generating answer from Gemini API: {e}")
            raise e


gemini_service = GeminiService()
