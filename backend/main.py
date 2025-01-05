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
logging.basicConfig(level=logging.INFO)

indexing_service = IndexingService()
watcher_service = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)

@app.on_event("startup")
async def startup_event():
    global watcher_service
    logger.info("Starting TechnicIA API...")
    
    os.makedirs(settings.DOCS_PATH, exist_ok=True)
    logger.info(f"Docs directory configured: {settings.DOCS_PATH}")
    
    watcher_service = WatcherService(settings.DOCS_PATH, indexing_service)
    await watcher_service.start()

@app.on_event("shutdown")
async def shutdown_event():
    if watcher_service:
        await watcher_service.stop()