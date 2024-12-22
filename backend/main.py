# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.routes import chat
from app.core.config import settings
from app.core.logging import setup_logging
from app.services.vector_store import VectorStore

logger = setup_logging()

app = FastAPI(
   title="TechnicIA API",
   description="API for technical documentation analysis",
   version="1.0.0"
)

# Configuration CORS détaillée
app.add_middleware(
   CORSMiddleware,
   allow_origins=["*"],  # En production, spécifier les origines exactes
   allow_credentials=True,
   allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
   allow_headers=["Content-Type", "Authorization", "accept", "Origin", 
                 "Access-Control-Request-Method", "Access-Control-Request-Headers"],
   expose_headers=["*"],
   max_age=600 # En secondes
)

# Routes racine
@app.get("/")
async def root():
   """Route racine pour vérifier que l'API fonctionne"""
   return {
       "status": "online",
       "service": "TechnicIA API",
       "version": "1.0.0"
   }

@app.get("/ping")
async def ping():
   """Endpoint simple pour tester la connexion"""
   return {"status": "success", "message": "pong!"}

# Routes API
app.include_router(chat.router, prefix="/api", tags=["chat"])

@app.on_event("startup")
async def startup_event():
   """
   Initialise les services au démarrage.
   """
   try:
       vector_store = VectorStore()
       await vector_store.init_collection()
       logger.info("Vector store initialized successfully")
   except Exception as e:
       logger.error(f"Error initializing services: {str(e)}")
       raise

@app.on_event("shutdown")
async def shutdown_event():
   """
   Nettoie les ressources lors de l'arrêt.
   """
   logger.info("Shutting down API...")

if __name__ == "__main__":
   import uvicorn
   uvicorn.run(
       "main:app",
       host=settings.API_HOST,
       port=settings.API_PORT,
       reload=True
   )