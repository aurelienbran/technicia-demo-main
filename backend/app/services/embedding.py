import httpx
import logging
import base64
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

    async def _make_request(self, inputs: List[Dict], batch_size: int = 32) -> List[List[float]]:
        try:
            all_embeddings = []
            
            # Traiter par lots
            for i in range(0, len(inputs), batch_size):
                batch = inputs[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(inputs) + batch_size - 1)//batch_size}")
                
                async with httpx.AsyncClient() as client:
                    payload = {
                        "model": "voyage-multi-1",
                        "inputs": [
                            {"content": content} for content in batch
                        ]
                    }
                    
                    try:
                        response = await client.post(
                            self.api_url,
                            headers=self.headers,
                            json=payload,
                            timeout=60.0
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        # Format de réponse selon la doc Voyage AI
                        embeddings = result["data"]
                        all_embeddings.extend(embeddings)
                        
                    except httpx.HTTPError as e:
                        logger.error(f"Error during API call: {e.response.text if hasattr(e, 'response') else str(e)}")
                        logger.error(f"Payload sent: {payload}")
                        raise
            
            return all_embeddings
                    
        except Exception as e:
            logger.error(f"Error in embedding generation: {str(e)}")
            raise
            
    async def get_multimodal_embeddings(self, documents: List[Dict[str, Any]]) -> List[List[float]]:
        """Génère des embeddings pour des documents texte et images."""
        if not documents:
            return []
            
        formatted_inputs = []
        current_content = []
        
        for doc in documents:
            if doc["type"] == "text":
                # Si on a déjà du contenu, on crée un nouvel input
                if current_content:
                    formatted_inputs.append(current_content)
                    current_content = []
                
                # Ajouter le texte comme un nouvel input
                current_content.append({"text": doc["text"]})
                formatted_inputs.append(current_content)
                current_content = []
            
            elif doc["type"] == "image" and "image" in doc:
                current_content.append({"image": {"data": doc["image"]}})
                if "context" in doc:
                    current_content.append({"text": doc["context"]})

        # Ajouter le dernier contenu s'il existe
        if current_content:
            formatted_inputs.append(current_content)

        if not formatted_inputs:
            logger.warning("No valid inputs found for embedding generation")
            return []

        logger.info(f"Generating embeddings for {len(formatted_inputs)} inputs")
        try:
            embeddings = await self._make_request(formatted_inputs, self.batch_size)
            return [emb["embedding"] for emb in embeddings]
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            return []