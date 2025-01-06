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

    async def _make_request(self, inputs: List[Dict[str, Any]], batch_size: int = 32) -> List[List[float]]:
        try:
            all_embeddings = []
            
            # Traiter par lots
            for i in range(0, len(inputs), batch_size):
                batch = inputs[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(inputs) + batch_size - 1)//batch_size}")
                
                async with httpx.AsyncClient() as client:
                    payload = {
                        "model": "voyage-multi-2",
                        "input": batch,
                        "input_type": "document"  # Optimisé pour les documents
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
                        embeddings = [item["embedding"] for item in result["data"]]
                        all_embeddings.extend(embeddings)
                        
                    except httpx.HTTPError as e:
                        logger.error(f"Error during API call: {e.response.text if hasattr(e, 'response') else str(e)}")
                        raise
            
            return all_embeddings
                    
        except Exception as e:
            logger.error(f"Error in embedding generation: {str(e)}")
            raise
            
    async def get_multimodal_embeddings(self, documents: List[Dict[str, Any]]) -> List[List[float]]:
        """Génère des embeddings pour des documents texte avec contexte."""
        if not documents:
            return []
            
        formatted_inputs = []
        for doc in documents:
            if doc["type"] == "text":
                # Ajouter directement le texte
                formatted_inputs.append(doc["text"])

        if not formatted_inputs:
            logger.warning("No valid inputs found for embedding generation")
            return []

        logger.info(f"Generating embeddings for {len(formatted_inputs)} inputs")
        try:
            return await self._make_request(formatted_inputs, self.batch_size)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            return []