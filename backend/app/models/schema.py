from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- Input Models ---

class ChunkMetadata(BaseModel):
    document_id: str
    document_title: str
    document_type: Optional[str] = None
    part_number: Optional[int] = None
    part_title: Optional[str] = None
    chapter_number: Optional[int] = None
    chapter_title: Optional[str] = None
    section_number: Optional[int] = None
    section_title: Optional[str] = None
    article_number: Optional[int] = None
    article_title: Optional[str] = None
    clause_number: Optional[int] = None
    clause_intro: Optional[str] = None
    point: Optional[str] = None
    hierarchy_path: List[Any] = Field(default_factory=list)

class Chunk(BaseModel):
    chunk_id: str
    node_type: str
    metadata: ChunkMetadata
    text: str

class IngestFileRequest(BaseModel):
    file_path: str = Field(..., description="Path to local JSON file containing chunks")

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User legal question")

# --- Output Models ---

class Source(BaseModel):
    chunk_id: str
    document_title: str
    article_title: Optional[str] = None
    article_number: Optional[int] = None
    clause_number: Any = None
    point: Optional[str] = None
    text: str
    rrf_score: float

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]

class IngestResponse(BaseModel):
    status: str
    message: str
    count: int
