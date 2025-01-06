import httpx
import logging
from typing import List, Union, Dict, Any
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
        self.batch_size = 32
        logger.info("Embedding service initialized")

    async def _make_request(self, inputs: List[Dict], batch_size: int = 32) -> List[Dict]:
        try:
            all_embeddings = []
            
            # Traiter par lots
            for i in range(0, len(inputs), batch_size):
                batch = inputs[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(inputs) + batch_size - 1)//batch_size}")
                
                async with httpx.AsyncClient() as client:
                    payload = {
                        "model": "voyage-multimodal-3",
                        "inputs": batch,
                        "input_type": "document"
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
                        
                        # Format de réponse selon la doc Voyage AI
                        embeddings = result.get("data", [])
                        all_embeddings.extend(embeddings)
                        
                        # Log des tokens utilisés
                        if "usage" in result:
                            usage = result["usage"]
                            logger.info(f"Tokens used - Text: {usage.get('text_tokens', 0)}, "
                                     f"Images: {usage.get('image_pixels', 0)} pixels, "
                                     f"Total: {usage.get('total_tokens', 0)}")
                        
                    except httpx.HTTPError as e:
                        logger.error(f"Error during API call: {e.response.text if hasattr(e, 'response') else str(e)}")
                        logger.error(f"Request payload: {payload}")
                        raise
            
            return [item["embedding"] for item in all_embeddings]
                    
        except Exception as e:
            logger.error(f"Error in embedding generation: {str(e)}")
            raise
            
    async def get_multimodal_embeddings(self, documents: List[Dict[str, Any]]) -> List[List[float]]:
        """Génère des embeddings pour des documents texte avec contexte."""
        if not documents:
            return []
            
        # Formater les inputs selon la documentation
        formatted_inputs = []
        for doc in documents:
            if doc["type"] == "text":
                # Pour le texte, créer un input avec un seul élément content
                formatted_input = {
                    "content": [{"text": doc["text"]}]
                }
                formatted_inputs.append(formatted_input)

        if not formatted_inputs:
            logger.warning("No valid inputs found for embedding generation")
            return []

        logger.info(f"Generating embeddings for {len(formatted_inputs)} inputs")
        try:
            return await self._make_request(formatted_inputs, self.batch_size)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            return []