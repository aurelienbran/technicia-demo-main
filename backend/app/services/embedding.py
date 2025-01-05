import httpx
import logging
import numpy as np
from typing import List, Union, Dict, Any
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
        self.batch_size = 32  # Limite batch pour optimiser
        logger.info("Embedding service initialized")

    async def _make_request(self, inputs: List[Dict[str, Any]]) -> Dict:
        try:
            async with httpx.AsyncClient() as client:
                if len(inputs) > self.batch_size:
                    logger.warning(f"Large batch size ({len(inputs)}) detected, splitting into chunks")
                    # Traiter par lots
                    all_embeddings = []
                    for i in range(0, len(inputs), self.batch_size):
                        batch = inputs[i:i + self.batch_size]
                        payload = {
                            "input": batch,
                            "model": "voyage-multimodal-3",
                            "encoding_format": None
                        }
                        response = await client.post(
                            self.api_url,
                            headers=self.headers,
                            json=payload,
                            timeout=30.0
                        )
                        response.raise_for_status()
                        all_embeddings.extend(response.json()["data"])
                    return {"data": all_embeddings}
                else:
                    payload = {
                        "input": inputs,
                        "model": "voyage-multimodal-3",
                        "encoding_format": None
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

    async def get_embedding_for_text(self, text: str) -> List[float]:
        """Génère un embedding pour du texte simple"""
        logger.debug(f"Generating embedding for text: {text[:100]}...")
        response = await self._make_request([{"text": text}])
        return response["data"][0]["embedding"]

    async def get_embedding_for_image(self, image_b64: str, context: str = "") -> List[float]:
        """Génère un embedding pour une image avec contexte optionnel"""
        input_data = {"image": {"data": image_b64}}
        if context:
            input_data["text"] = context
        response = await self._make_request([input_data])
        return response["data"][0]["embedding"]

    async def get_multimodal_embeddings(self, documents: List[Dict[str, Any]]) -> List[List[float]]:
        """Génère des embeddings pour une liste de documents multimodaux"""
        if not documents:
            return []
        
        # Format correct pour chaque document
        formatted_inputs = []
        for doc in documents:
            if "text" in doc:
                formatted_inputs.append({"text": doc["text"]})
            elif "image" in doc:
                input_data = {"image": {"data": doc["image"]}}
                if "context" in doc:
                    input_data["text"] = doc["context"]
                formatted_inputs.append(input_data)

        logger.debug(f"Generating embeddings for {len(formatted_inputs)} inputs")
        response = await self._make_request(formatted_inputs)
        return [item["embedding"] for item in response["data"]]

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calcule la similarité cosinus entre deux embeddings"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        return dot_product / (norm1 * norm2)