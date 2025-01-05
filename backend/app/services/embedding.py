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

    async def _make_request(self, inputs: Union[str, List[Dict]]) -> Dict:
        try:
            async with httpx.AsyncClient() as client:
                payload = {
                    "input": inputs if isinstance(inputs, list) else [{"text": inputs}],
                    "model": "voyage-multimodal-3",
                }
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
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

    async def get_embedding(self, text: str) -> List[float]:
        logger.debug(f"Generating embedding for text: {text[:100]}...")
        response = await self._make_request(text)
        return response["data"][0]["embedding"]

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        logger.debug(f"Generating embeddings for {len(texts)} texts")
        inputs = [{"text": text} for text in texts]
        response = await self._make_request(inputs)
        return [item["embedding"] for item in response["data"]]

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2)

    async def chunk_text(self, text: str, chunk_size: int = 1500, overlap: int = 300) -> List[str]:
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                for char in ['. ', '\n', ' ']:
                    last_pos = text[start:end].rfind(char)
                    if last_pos != -1:
                        end = start + last_pos + 1
                        break
            chunks.append(text[start:end].strip())
            start = end - overlap
        return chunks

    async def preprocess_text(self, text: str) -> str:
        text = text.replace('\n', ' ').replace('\r', ' ')
        text = ' '.join(text.split())
        return text