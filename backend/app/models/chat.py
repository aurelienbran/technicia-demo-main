from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    query: str
    limit: int = 5

class QueryResponse(BaseModel):
    matches: List[Dict[str, Any]]
    answer: str
    query: Optional[str] = None
    error: Optional[str] = None

class IndexResponse(BaseModel):
    status: str
    metadata: Dict[str, Any]
    error: Optional[str] = None