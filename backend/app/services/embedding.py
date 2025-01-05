import httpx
import logging
import numpy as np
from typing import List, Union, Dict
from ..core.config import settings

logger = logging.getLogger("technicia.embedding")

class EmbeddingService:
    def __init__(self):
        self.api_key = settings.VOYAGE_API_KEY
        self.api_url = "https://api.voyageai.com/v1/embeddings"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logger.info("Embedding service initialized")

    async def _make_request(self, texts: Union[str, List[str]], input_type: str = "document") -> Dict:
        """
        Fait une requête à l'API Voyage AI.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json={
                        "input": texts,
                        "model": "voyage-multimodal-3",
                        "input_type": input_type,
                        "truncation": True
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error calling Voyage AI API: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating embeddings: {str(e)}")
            raise

    async def get_embedding(self, text: str, input_type: str = "document") -> List[float]:
        """
        Génère un embedding pour un seul texte.
        """
        logger.debug(f"Generating embedding for text: {text[:100]}...")
        response = await self._make_request(text, input_type)
        return response["data"][0]["embedding"]

    async def get_embeddings(self, texts: List[str], input_type: str = "document") -> List[List[float]]:
        """
        Génère des embeddings pour une liste de textes.
        """
        if not texts:
            return []

        logger.debug(f"Generating embeddings for {len(texts)} texts")
        response = await self._make_request(texts, input_type)
        return [item["embedding"] for item in response["data"]]

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calcule la similarité cosinus entre deux embeddings.
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        return dot_product / (norm1 * norm2)

    async def chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 300) -> List[str]:
        """
        Découpe un texte long en chunks pour l'embedding.
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        
        while start < len(text):
            # Trouver la fin du chunk
            end = start + chunk_size
            
            # Ajuster à la fin d'une phrase ou d'un mot si possible
            if end < len(text):
                # Chercher le dernier point ou espace
                for char in ['. ', '\n', ' ']:
                    last_pos = text[start:end].rfind(char)
                    if last_pos != -1:
                        end = start + last_pos + 1
                        break
            
            chunks.append(text[start:end].strip())
            start = end - overlap

        logger.debug(f"Split text into {len(chunks)} chunks")
        return chunks

    async def preprocess_text(self, text: str) -> str:
        """
        Prétraite le texte avant l'embedding.
        """
        # Nettoyage basique
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = ' '.join(text.split())  # Normalise les espaces
        return text