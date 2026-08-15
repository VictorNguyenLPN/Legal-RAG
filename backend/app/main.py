import logging
import sys
import json
from contextlib import asynccontextmanager
# pyrefly: ignore [missing-import]
import uvicorn
# pyrefly: ignore [missing-import]
from uvicorn.logging import ColourizedFormatter
# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.api.routes import router
from backend.app.database.vector_db import vector_db
from backend.app.services.rag_service import rag_service

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
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    corpus_path = settings.DATA_DIR / "corpus.json"

    if vector_db.is_empty():
        logger.warning("Database is empty. Finding local corpus ...")
        if corpus_path.exists() and corpus_path.is_file():
            logger.info(f"Corpus found at {corpus_path}")
            try:
                with open(corpus_path, "r", encoding="utf-8") as f:
                    raw_chunks = json.load(f)
                corpus_len = len(raw_chunks) if isinstance(raw_chunks, list) else 0
                logger.info(f"Read corpus success: {corpus_len} chunks")
            except Exception as e:
                logger.error(f"Failed to read corpus: {e}")
                raw_chunks = None
                corpus_len = 0

            try:
                count = rag_service.ingest_chunks(raw_chunks)
                logger.info(f"Ingest corpus success: {count} chunks")
            except Exception as e:
                logger.error(f"Failed to ingest: {e}")
        else:
            logger.warning(f"Corpus not found.")
    else:
        logger.info(f"Database is ready: {len(vector_db)} chunks")
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="Legal Document QA using Hybrid Search and Gemini",
    version="2.6.1",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
