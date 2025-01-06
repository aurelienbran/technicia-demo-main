import httpx
import logging
from typing import List, Dict, Any
from ..core.config import settings

logger = logging.getLogger("technicia.embedding")

class EmbeddingService:
    def __init__(self):
        self.api_key = settings.VOYAGE_API_KEY
        self.api_url = "https://api.voyageai.com/v1/multimodalembeddings"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.batch_size = 20
        logger.info("Embedding service initialized")

    async def _make_request(self, inputs: List[Dict], batch_size: int = 20) -> List[List[float]]:
        try:
            all_embeddings = []
            
            # Traiter par lots
            for i in range(0, len(inputs), batch_size):
                batch = inputs[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(inputs) + batch_size - 1)//batch_size}")
                
                async with httpx.AsyncClient() as client:
                    # Format selon la documentation officielle
                    payload = {
                        "model": "voyage-multimodal-3",
                        "inputs": batch,
                        "input_type": "document",
                        "truncation": True
                    }
                    
                    try:
                        logger.debug(f"Sending payload: {payload}")
                        response = await client.post(
                            self.api_url,
                            headers=self.headers,
                            json=payload,
                            timeout=60.0
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        # Extraire les embeddings
                        for item in result.get("data", []):
                            if "embedding" in item:
                                all_embeddings.append(item["embedding"])
                        
                        # Log des tokens et pixels utilisés
                        if "usage" in result:
                            usage = result["usage"]
                            logger.info(
                                f"Usage - Text tokens: {usage.get('text_tokens', 0)}, "
                                f"Image pixels: {usage.get('image_pixels', 0)}, "
                                f"Total tokens: {usage.get('total_tokens', 0)}"
                            )
                    except httpx.HTTPError as e:
                        logger.error(f"Error during API call: {str(e)}")
                        if hasattr(e, 'response'):
                            logger.error(f"Response content: {e.response.text}")
                        logger.error(f"Request payload: {payload}")
                        raise
            
            return all_embeddings
                    
        except Exception as e:
            logger.error(f"Error in embedding generation: {str(e)}")
            raise
            
    async def get_multimodal_embeddings(self, documents: List[Dict[str, Any]]) -> List[List[float]]:
        """Génère des embeddings pour des documents texte et images."""
        if not documents:
            return []
            
        # Transformer les documents en format compatible avec l'API
        formatted_inputs = []
        for doc in documents:
            if doc["type"] == "text":
                # Format pour le texte selon la documentation
                content = [{
                    "text": doc["text"].strip()
                }]
                formatted_inputs.append({"content": content})

        if not formatted_inputs:
            logger.warning("No valid inputs found for embedding generation")
            return []

        logger.info(f"Generating embeddings for {len(formatted_inputs)} inputs")
        try:
            return await self._make_request(formatted_inputs, self.batch_size)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            return []