from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import anthropic
import aiohttp
import os
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from qdrant_client import QdrantClient
import fitz  # PyMuPDF
from dotenv import load_dotenv
import logging
from pathlib import Path
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
load_dotenv()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Constantes
DOCS_DIR = "docs"
Path(DOCS_DIR).mkdir(exist_ok=True)

# Initialisation des clients
try:
    claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    qdrant = QdrantClient("localhost", port=6333)
except Exception as e:
    logger.error(f"Erreur d'initialisation des clients: {e}")
    raise

# Création de la collection Qdrant
async def init_qdrant():
    for attempt in range(3):
        try:
            qdrant.create_collection(
                collection_name="documents",
                vectors_config={"size": 1024, "distance": "Cosine"}
            )
            break
        except Exception as e:
            if attempt == 2:
                logger.error(f"Impossible de créer la collection: {e}")
            await asyncio.sleep(2)

@app.on_event("startup")
async def startup_event():
    await init_qdrant()

async def generate_embedding(text: str, retries=3) -> list:
    """Génère un embedding avec gestion des erreurs."""
    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {os.getenv('VOYAGE_API_KEY')}",
                    "Content-Type": "application/json"
                }
                async with session.post(
                    "https://api.voyageai.com/v1/embeddings",
                    headers=headers,
                    json={"model": "voyage-01", "input": text},
                    timeout=10
                ) as response:
                    if response.status != 200:
                        raise HTTPException(status_code=response.status, detail="Erreur Voyage AI")
                    result = await response.json()
                    return result['data'][0]['embedding']
        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"Échec de génération d'embedding: {e}")
                raise
            await asyncio.sleep(2)

async def index_document(filepath: str):
    """Indexe un document."""
    try:
        # Extraction du texte
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        # Génération de l'embedding
        embedding = await generate_embedding(text)

        # Stockage dans Qdrant
        qdrant.upsert(
            collection_name="documents",
            points=[{
                "id": abs(hash(filepath)),
                "vector": embedding,
                "payload": {
                    "content": text[:100000],  # Limite pour éviter les problèmes de mémoire
                    "filepath": filepath,
                    "indexed_at": str(datetime.now())
                }
            }]
        )
        logger.info(f"Document indexé avec succès: {filepath}")
    except Exception as e:
        logger.error(f"Erreur d'indexation pour {filepath}: {e}")
        raise

class DocumentHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            asyncio.run(index_document(event.src_path))

# Démarrage de la surveillance du dossier
observer = Observer()
observer.schedule(DocumentHandler(), DOCS_DIR, recursive=False)
observer.start()

@app.post("/chat")
async def chat(query: str):
    try:
        # Recherche sémantique
        query_embedding = await generate_embedding(query)
        search_results = qdrant.search(
            collection_name="documents",
            query_vector=query_embedding,
            limit=3,
            score_threshold=0.7
        )
        
        # Construction du contexte
        context = "\n\n".join([hit.payload["content"] for hit in search_results])
        if len(context) > 4000:
            context = context[:4000] + "..."
        
        # Réponse de Claude
        response = claude.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1024,
            messages=[
                {
                    "role": "system",
                    "content": "Tu es TechnicIA, un assistant technique professionnel. Utilise le contexte fourni pour répondre aux questions de manière précise et concise."
                },
                {
                    "role": "user",
                    "content": f"Contexte: {context}\n\nQuestion: {query}"
                }
            ]
        )
        
        return {"response": response.content[0].text}
    except Exception as e:
        logger.error(f"Erreur de chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Endpoint de vérification de santé."""
    return {"status": "healthy"}

@app.on_event("shutdown")
def shutdown_event():
    """Nettoyage propre à l'arrêt."""
    observer.stop()
    observer.join()