from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anthropic
import os
from dotenv import load_dotenv
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import fitz  # PyMuPDF
from qdrant_client import QdrantClient
import aiohttp
from datetime import datetime

# Configuration du logging et des dossiers
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DOCS_DIR = "docs"
Path(DOCS_DIR).mkdir(exist_ok=True)

# Configuration de base
load_dotenv()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Initialisation des clients
try:
    claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    qdrant = QdrantClient("localhost", port=6333)
    
    # Création de la collection Qdrant si elle n'existe pas
    try:
        qdrant.get_collection('documents')
    except:
        qdrant.create_collection(
            collection_name='documents',
            vectors_config={"size": 1024, "distance": "Cosine"}
        )
        
except Exception as e:
    logger.error(f"Erreur d'initialisation des clients: {e}")
    raise

# Fonction pour générer les embeddings
async def generate_embedding(text: str, retries=3):
    """Génère un embedding avec Voyage AI"""
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

# Fonction d'indexation des documents
async def index_document(filepath: str):
    """Indexe un document PDF dans Qdrant"""
    try:
        logger.info(f"Début de l'indexation du document: {filepath}")
        
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
                    "content": text[:100000],
                    "filepath": filepath,
                    "indexed_at": str(datetime.now())
                }
            }]
        )
        logger.info(f"Document indexé avec succès: {filepath}")
    except Exception as e:
        logger.error(f"Erreur d'indexation pour {filepath}: {e}")
        raise

# Handler pour la surveillance des fichiers
class DocumentHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            logger.info(f"Nouveau fichier PDF détecté: {event.src_path}")
            import asyncio
            asyncio.run(index_document(event.src_path))

# Démarrage de la surveillance du dossier
observer = Observer()
observer.schedule(DocumentHandler(), DOCS_DIR, recursive=False)
observer.start()
logger.info(f"Surveillance du dossier {DOCS_DIR} démarrée")

# [Le reste du code (chat et health_check) reste identique...]

# Nettoyage à l'arrêt
@app.on_event("shutdown")
def shutdown_event():
    observer.stop()
    observer.join()