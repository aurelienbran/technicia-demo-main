from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.api.routes import chat
from app.core.config import settings
from app.services.watcher import WatcherService
from app.services.indexing import IndexingService
from app.services.storage import StorageService
from app.services.embedding import EmbeddingService
from app.services.vector_store import VectorStore
import logging

logger = logging.getLogger("technicia.main")

app = FastAPI(title="TechnicIA API")

# Configuration du niveau de logging
logging.basicConfig(level=logging.INFO)

# Initialisation des services
storage_service = StorageService(settings.get_docs_path())
embedding_service = EmbeddingService()
vector_store = VectorStore()
indexing_service = IndexingService(embedding_service, vector_store, storage_service)
watcher_service = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    global watcher_service
    logger.info("Starting TechnicIA API...")
    
    # Configuration du dossier des documents
    docs_path = settings.get_docs_path()
    logger.info(f"Docs directory configured: {docs_path}")
    
    # Vérification des permissions du dossier
    perms = storage_service.check_permissions(docs_path)
    logger.info(f"Directory permissions: {perms}")
    
    # Démarrage du service de surveillance
    watcher_service = WatcherService(str(docs_path), indexing_service)
    await watcher_service.start()
    logger.info("Watcher service started")

@app.on_event("shutdown")
async def shutdown_event():
    global watcher_service
    logger.info("Shutting down TechnicIA API...")
    if watcher_service:
        await watcher_service.stop()
        logger.info("Watcher service stopped")
