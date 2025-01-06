from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import logging
import os
import tempfile
from typing import List

from ...models.chat import QueryRequest, QueryResponse, IndexResponse
from ...services.indexing import IndexingService
from ...core.config import settings

router = APIRouter()
logger = logging.getLogger("technicia.api")
indexing_service = IndexingService()

@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest) -> QueryResponse:
    try:
        result = await indexing_service.search(
            query=request.query,
            limit=request.limit
        )
        
        if "error" in result and result["error"]:
            raise HTTPException(status_code=500, detail=result["error"])
            
        return QueryResponse(
            matches=result["matches"],
            query=request.query
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))