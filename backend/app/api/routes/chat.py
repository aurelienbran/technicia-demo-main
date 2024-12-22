# app/api/routes/chat.py

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import logging
from typing import List
import tempfile
import os

from ...models.chat import QueryRequest, QueryResponse, IndexResponse
from ...services.indexing import IndexingService
from ...core.config import settings

router = APIRouter()
logger = logging.getLogger("technicia.api")
indexing_service = IndexingService()

@router.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Recherche dans les documents et génère une réponse.
    """
    try:
        result = await indexing_service.search(
            query=request.query,
            limit=request.limit,
            score_threshold=request.score_threshold
        )
        return result
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/index/file", response_model=IndexResponse)
async def index_file(file: UploadFile = File(...)):
    """
    Indexe un fichier PDF unique.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Sauvegarder temporairement le fichier
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Indexer le document
        result = await indexing_service.index_document(tmp_path)
        
        # Nettoyer
        os.unlink(tmp_path)
        
        return result
    except Exception as e:
        logger.error(f"Error indexing file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/index/directory", response_model=List[IndexResponse])
async def index_directory(directory: str):
    """
    Indexe tous les PDFs dans un répertoire.
    """
    try:
        results = await indexing_service.index_directory(directory)
        return results
    except Exception as e:
        logger.error(f"Error indexing directory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """
    Vérifie l'état des services.
    """
    try:
        # Vérifier Qdrant
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