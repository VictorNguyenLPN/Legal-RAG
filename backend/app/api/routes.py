import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, status
from backend.app.models.schema import (
    Chunk, IngestFileRequest, IngestResponse, QueryRequest, QueryResponse
)
from backend.app.services.rag_service import rag_service
from backend.app.database.vector_db import vector_db

router = APIRouter()

@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_from_body(chunks: List[Chunk]):
    """
    Ingest a list of document chunks directly from the HTTP request body.
    """
    try:
        # Convert Pydantic models back to raw dicts for services
        raw_chunks = [chunk.model_dump() for chunk in chunks]
        count = rag_service.ingest_chunks(raw_chunks)
        return IngestResponse(
            status="success",
            message=f"Successfully ingested {count} chunks.",
            count=count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest chunks: {str(e)}"
        )

@router.post("/ingest-file", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_from_file(payload: IngestFileRequest):
    """
    Ingest document chunks from a local JSON file path on the server.
    """
    path = Path(payload.file_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File not found at: {payload.file_path}"
        )
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_chunks = json.load(f)
            
        if not isinstance(raw_chunks, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="JSON file content must be a list of chunks."
            )
            
        count = rag_service.ingest_chunks(raw_chunks)
        return IngestResponse(
            status="success",
            message=f"Successfully ingested {count} chunks from file.",
            count=count
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest chunks from file: {str(e)}"
        )

@router.post("/query", response_model=QueryResponse)
async def query_rag(payload: QueryRequest):
    """
    Query the Hybrid Legal RAG pipeline.
    """
    if vector_db.is_empty():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vector database is empty. Please run /ingest first."
        )
        
    try:
        result = rag_service.query(payload.query)
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query execution failed: {str(e)}"
        )

@router.get("/status")
async def get_status():
    """
    Get the initialization status of the RAG system database.
    """
    is_empty = vector_db.is_empty()
    chunk_count = len(vector_db.chunks)
    return {
        "database_initialized": not is_empty,
        "chunk_count": chunk_count,
        "has_embeddings": vector_db.embeddings is not None
    }
