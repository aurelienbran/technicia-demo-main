from fastapi import APIRouter, HTTPException, Response
from typing import Dict
from ...services.indexing import IndexingService

router = APIRouter()
indexing_service = IndexingService()

@router.delete("/api/vectors/{filename}")
async def delete_vectors(filename: str):
    try:
        await indexing_service.vector_store.delete_vectors_by_filename(filename)
        return {"status": "success", "message": f"Vectors deleted for {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))