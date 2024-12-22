from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class QueryRequest(BaseModel):
    query: str = Field(..., description="La question de l'utilisateur")
    limit: Optional[int] = Field(5, description="Nombre maximum de résultats à retourner")
    score_threshold: Optional[float] = Field(0.7, description="Seuil minimal de similarité")

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict]
    context_used: int

class IndexResponse(BaseModel):
    status: str
    file: str
    chunks_processed: Optional[int]
    metadata: Optional[Dict]
    error: Optional[str]