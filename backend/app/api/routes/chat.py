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
async def query_documents(request: QueryRequest):
    try:
        result = await indexing_service.search(
            query=request.query,
            limit=request.limit
        )
        return result
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/index/file", response_model=IndexResponse)
async def index_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            result = await indexing_service.index_document(tmp_path)
            if not result.get('metadata'):
                result['metadata'] = {}
            if result.get('error') is None:
                result['error'] = ''
            return result
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        logger.error(f"Error indexing file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    try:
        collection_info = await indexing_service.vector_store.get_collection_info()
        return {
            "status": "healthy",
            "vector_store": {
                "status": "connected",
                "collection": collection_info
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )