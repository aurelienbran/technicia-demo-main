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
        if 'error' in result:
            return JSONResponse(
                status_code=500,
                content={
                    "matches": [],
                    "error": result["error"]
                }
            )
            
        # Enrichir les résultats avec le contenu du texte
        enriched_matches = []
        for match in result["matches"]:
            enriched_matches.append({
                "id": match["id"],
                "score": match["score"],
                "content": match["content"],
                "metadata": match["metadata"],
                "page": match["page"]
            })
            
        return JSONResponse(
            status_code=200,
            content={
                "matches": enriched_matches,
                "query": request.query
            }
        )
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "matches": [],
                "error": str(e)
            }
        )