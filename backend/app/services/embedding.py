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
        self.batch_size = 32
        logger.info("Embedding service initialized")

    async def _make_request(self, inputs: List[Dict[str, Any]], batch_size: int = 32) -> Dict:
        try:
            all_embeddings = []
            for i in range(0, len(inputs), batch_size):
                batch = inputs[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(inputs) + batch_size - 1)//batch_size}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.api_url,
                        headers=self.headers,
                        json={
                            "model": "voyage-multimodal-3",
                            "input": batch
                        },
                        timeout=60.0
                    )
                    response.raise_for_status()
                    batch_result = response.json()
                    all_embeddings.extend(batch_result["data"])
            
            return {"data": all_embeddings}
                    
        except httpx.HTTPError as e:
            logger.error(f"Error calling Voyage AI API: {str(e)}")
            raise
            
    async def get_multimodal_embeddings(self, documents: List[Dict[str, Any]]) -> List[List[float]]:
        if not documents:
            return []
            
        formatted_inputs = []
        for doc in documents:
            if doc["type"] == "text":
                formatted_inputs.append(doc["text"])
            elif doc["type"] == "image":
                formatted_inputs.append({
                    "image": doc["image"],
                    "text": doc["context"] if doc["context"] else ""
                })

        logger.info(f"Generating embeddings for {len(formatted_inputs)} inputs")
        response = await self._make_request(formatted_inputs, self.batch_size)
        return [item["embedding"] for item in response["data"]]