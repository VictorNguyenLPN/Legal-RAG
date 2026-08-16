import os
from pathlib import Path
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # App Config
    APP_NAME: str = "Legal RAG"
    API_V1_STR: str = "/api/v1"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_DIR: Path = DATA_DIR / "db"
    
    # Gemini API settings
    # The new google-genai SDK uses GEMINI_API_KEY by default.
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Jina AI Reranker settings
    JINA_API_KEY: str = os.getenv("JINA_API_KEY", "")
    JINA_RERANK_MODEL: str = "jina-reranker-v2-base-multilingual"
    
    # Models
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    GENERATION_MODEL: str = "gemini-3.1-flash-lite"
    
    # Retrieval parameters
    DENSE_TOP_K: int = 10
    SPARSE_TOP_K: int = 10
    RRF_TOP_N: int = 5
    RRF_K: int = 60

    # Qdrant settings
    QDRANT_URL: str = ""
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "legal_chunks"
    
    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.DB_DIR.mkdir(parents=True, exist_ok=True)

