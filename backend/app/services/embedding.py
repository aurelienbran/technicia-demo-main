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
        self.batch_size = 20  # Maximum recommandé par la doc
        logger.info("Embedding service initialized")

    async def _make_request(self, inputs: List[str], batch_size: int = 20) -> List[List[float]]:
        try:
            all_embeddings = []
            
            # Traiter par lots
            for i in range(0, len(inputs), batch_size):
                batch = inputs[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(inputs) + batch_size - 1)//batch_size}")
                
                async with httpx.AsyncClient() as client:
                    payload = {
                        "model": "voyage-multimodal-3",
                        "inputs": [{
                            "text": text
                        } for text in batch]
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
                        
                        # Extraire les embeddings de la réponse
                        batch_embeddings = []
                        for item in result.get("data", []):
                            if "embedding" in item:
                                batch_embeddings.append(item["embedding"])
                        all_embeddings.extend(batch_embeddings)
                        
                        # Log des tokens utilisés
                        if "usage" in result:
                            usage = result["usage"]
                            logger.info(f"Tokens used - Text: {usage.get('text_tokens', 0)}, "
                                     f"Total: {usage.get('total_tokens', 0)}")
                        
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
        """Génère des embeddings pour des documents texte."""
        if not documents:
            return []
            
        # Extraire uniquement le texte des documents
        texts = []
        for doc in documents:
            if doc["type"] == "text" and "text" in doc:
                texts.append(doc["text"])

        if not texts:
            logger.warning("No valid text inputs found for embedding generation")
            return []

        logger.info(f"Generating embeddings for {len(texts)} text inputs")
        try:
            embeddings = await self._make_request(texts, self.batch_size)
            if not embeddings:
                logger.error("No embeddings generated from API response")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            return []