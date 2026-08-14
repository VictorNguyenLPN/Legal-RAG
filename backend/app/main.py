import logging
import sys
# pyrefly: ignore [missing-import]
from uvicorn.logging import ColourizedFormatter

# Configure Logging to match FastAPI/Uvicorn colourized style at the very top
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ColourizedFormatter(
    fmt="%(levelprefix)s %(message)s",
    use_colors=True
))

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
    force=True
)
# Silence verbose request logs from httpx/http client library
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Now import local modules, so all their startup logs print at INFO level
from contextlib import asynccontextmanager
# pyrefly: ignore [missing-import]
import uvicorn
# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    import json
    from backend.app.database.vector_db import vector_db
    from backend.app.services.rag_service import rag_service

    corpus_path = settings.DATA_DIR / "corpus_1.json"

    # Explicitly log connection target and current status
    db_type = "Qdrant Cloud" if vector_db.cloud_inference else "Local Qdrant"
    logger.info(f"Targeting Database: {db_type}")

    logger.info("Checking for corpus.json at startup...")
    if corpus_path.exists() and corpus_path.is_file():
        logger.info(f"Found corpus.json at {corpus_path}")
        
        try:
            with open(corpus_path, "r", encoding="utf-8") as f:
                raw_chunks = json.load(f)
            corpus_len = len(raw_chunks) if isinstance(raw_chunks, list) else 0
        except Exception as e:
            logger.error(f"Failed to read corpus.json: {e}")
            raw_chunks = None
            corpus_len = 0
            
        is_empty = vector_db.is_empty()
        current_count = len(vector_db)
        logger.info(f"Checking if {db_type} is empty or incomplete... (Current points: {current_count}/{corpus_len})")
        
        # Re-ingest if database is empty or has less than 95% of the corpus chunks
        need_ingest = is_empty or (corpus_len > 0 and current_count < corpus_len * 0.95)
        
        if need_ingest:
            if not is_empty:
                logger.warning(f"Database collection '{vector_db.collection_name}' is incomplete/partially ingested ({current_count}/{corpus_len} points). Re-creating clean collection...")
                try:
                    vector_db.client.delete_collection(vector_db.collection_name)
                    vector_db._ensure_collection(vector_size=384)
                except Exception as ex:
                    logger.error(f"Failed to re-create collection: {ex}")
            
            logger.info(f"Starting automatic ingestion of {corpus_len} chunks into Qdrant...")
            try:
                if isinstance(raw_chunks, list):
                    count = rag_service.ingest_chunks(raw_chunks)
                    logger.info(f"Successfully auto-ingested {count} chunks into Qdrant.")
                else:
                    logger.error("Auto-ingestion failed: corpus.json is not a list of chunks.")
            except Exception as e:
                logger.error(f"Failed to perform auto-ingestion: {e}")
        else:
            logger.info(f"{db_type} already contains complete collection '{vector_db.collection_name}' ({current_count} points). Skipping auto-ingestion.")
    else:
        logger.info("corpus.json not found in data directory. System is ready for manual upload/ingestion.")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Legal Document QA MVP using Hybrid Search and Google Gemini",
    version="2.3.2",
    lifespan=lifespan
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


@app.get("/")
def read_root():
    return {
        "app": settings.APP_NAME,
        "docs_url": "/docs",
        "status": "online"
    }

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
