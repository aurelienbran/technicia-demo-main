from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
from routers import pdf_router

# Version simplifiée pour le démarrage
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

# Ajout du router PDF
app.include_router(pdf_router.router)

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

# Route simple de chat pour les tests
@app.post("/api/query")
async def chat_query(request: Request):
    body = await request.json()
    return {
        "response": "Test response",
        "query": body.get("query", ""),
        "status": "success"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )