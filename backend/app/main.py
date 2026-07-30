import logging
# pyrefly: ignore [missing-import]
import uvicorn
# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.api.routes import router

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="Legal Document QA MVP using Hybrid Search and Google Gemini",
    version="1.0.0"
)

# Enable CORS for frontend compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes directly at the root (matching /ingest and /query)
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    import json
    from backend.app.database.vector_db import vector_db
    from backend.app.services.rag_service import rag_service

    corpus_path = settings.DATA_DIR / "corpus.json"
    embeddings_path = settings.DB_DIR / "embeddings.npy"

    logger.info("Checking for corpus.json at startup...")
    if corpus_path.exists() and corpus_path.is_file():
        logger.info(f"Found corpus.json at {corpus_path}")
        if not embeddings_path.exists():
            logger.info("Database embeddings (.npy) not found. Starting automatic ingestion...")
            try:
                with open(corpus_path, "r", encoding="utf-8") as f:
                    raw_chunks = json.load(f)

                if isinstance(raw_chunks, list):
                    count = rag_service.ingest_chunks(raw_chunks)
                    logger.info(f"Successfully auto-ingested {count} chunks.")
                else:
                    logger.error("Auto-ingestion failed: corpus.json is not a list of chunks.")
            except Exception as e:
                logger.error(f"Failed to perform auto-ingestion: {e}")
        else:
            logger.info("Database embeddings (.npy) already exist. Skipping auto-ingestion.")
    else:
        logger.info("corpus.json not found in data directory. System is ready for manual upload/ingestion.")


@app.get("/")
def read_root():
    return {
        "app": settings.APP_NAME,
        "docs_url": "/docs",
        "status": "online"
    }

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
