import os
import fitz
import shutil
import tempfile
import stat
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import io
from .vector_store import VectorStore
from .embedding import EmbeddingService
from .claude import ClaudeService

logger = logging.getLogger("technicia.indexing")

MAX_IMAGE_SIZE = (1920, 1080)

class IndexingService:
    def __init__(self):
        self.vector_store = VectorStore()
        self.embedding_service = EmbeddingService()
        self.claude_service = ClaudeService()
        self.chunk_size = 1000
        self.overlap = 200
        self.max_retries = 3
        self.retry_delay = 1

    async def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        try:
            # Générer l'embedding de la requête
            query_embedding = await self.embedding_service.get_multimodal_embeddings([[query]])
            if not query_embedding or not query_embedding[0]:
                return {
                    "matches": [],
                    "answer": "Désolé, je n'ai pas pu traiter votre requête.",
                    "error": "Failed to generate query embedding"
                }

            # Rechercher les documents similaires
            matches = await self.vector_store.search(
                query_vector=query_embedding[0],
                limit=limit
            )

            if not matches:
                return {
                    "matches": [],
                    "answer": "Désolé, je n'ai pas trouvé d'information pertinente dans la documentation.",
                    "query": query
                }

            # Générer une réponse avec Claude
            answer = await self.claude_service.get_response(query, matches)

            return {
                "matches": matches,
                "answer": answer,
                "query": query
            }

        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return {
                "matches": [],
                "answer": "Une erreur s'est produite lors du traitement de votre demande.",
                "error": str(e)
            }