from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.api.routes import chat
from app.core.config import settings
from app.services.watcher import WatcherService
from app.services.indexing import IndexingService
import logging

logger = logging.getLogger("technicia.main")

app = FastAPI(title="TechnicIA API")

# Configuration du niveau de logging
logging.basicConfig(level=logging.INFO)

# Services
indexing_service = IndexingService()
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
    
    # Configurer le dossier docs
    docs_path = os.path.join(os.path.dirname(__file__), "docs")
    os.makedirs(docs_path, exist_ok=True)
    logger.info(f"Docs directory configured: {docs_path}")
    
    # Démarrer le service de surveillance
    watcher_service = WatcherService(docs_path, indexing_service)
    await watcher_service.start()
    logger.info("Watcher service started")

@app.on_event("shutdown")
async def shutdown_event():
    global watcher_service
    logger.info("Shutting down TechnicIA API...")
    if watcher_service:
        await watcher_service.stop()
        logger.info("Watcher service stopped")
