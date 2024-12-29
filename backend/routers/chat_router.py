from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["chat"])

class Query(BaseModel):
    query: str
    context: str = None

@router.post("/query")
async def query(query: Query):
    if not query.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Pour le moment, on renvoie une réponse simulée
    return {"response": f"Test response for: {query.query}"}