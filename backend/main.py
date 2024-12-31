from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.api.routes import chat
from app.core.config import settings
from app.services.watcher import WatcherService
from app.services.indexing import IndexingService

app = FastAPI(title="TechnicIA API")

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
    docs_path = os.path.join("docs")
    if not os.path.exists(docs_path):
        os.makedirs(docs_path)
        
    watcher = WatcherService(docs_path, IndexingService())
    await watcher.start()