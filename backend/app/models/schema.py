# pyrefly: ignore [missing-import]
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

class Message(BaseModel):
    role: str = Field(..., description="Role of the sender: user or assistant")
    content: str = Field(..., description="Content of the message")

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User legal question")
    history: Optional[List[Message]] = Field(default=None, description="Conversation history")

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
    token_details: Optional[Dict[str, float]] = None
    timing_details: Optional[Dict[str, float]] = None

class IngestResponse(BaseModel):
    status: str
    message: str
    count: int
