from pydantic import BaseModel, Field
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

class Source(BaseModel):
    id: int
    score: float
    payload: dict

class QueryResponse(BaseModel):
    answer: str
    sources: List[Source]

class IndexResponse(BaseModel):
    status: str
    file: Optional[str] = None
    chunks_processed: Optional[int] = 0
    metadata: Optional[dict] = Field(default={})
    error: Optional[str] = Field(default=None)