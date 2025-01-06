import httpx
import logging
from typing import List, Dict, Any
from ..core.config import settings

logger = logging.getLogger("technicia.embedding")

class EmbeddingService:
    def __init__(self):
        self.api_key = settings.VOYAGE_API_KEY
        self.api_url = "https://api.voyageai.com/v1/embeddings"  # Endpoint normal pour le texte
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.batch_size = 20
        logger.info("Embedding service initialized")

    async def _make_request(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        try:
            all_embeddings = []
            
            # Traiter par lots
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
                
                async with httpx.AsyncClient() as client:
                    # Format simple pour l'API embeddings
                    payload = {
                        "model": "voyage-2",
                        "input": batch,
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
                        
                        # Format de réponse pour l'API embeddings
                        batch_embeddings = [item["embedding"] for item in result["data"]]
                        all_embeddings.extend(batch_embeddings)
                        
                        # Log des tokens utilisés
                        if "usage" in result:
                            logger.info(f"Tokens used: {result['usage']['total_tokens']}")
                            
                    except httpx.HTTPError as e:
                        logger.error(f"Error during API call: {str(e)}")
                        if hasattr(e, 'response'):
                            logger.error(f"Response content: {e.response.text}")
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
                text = doc["text"].strip()
                if text:  # Vérifier que le texte n'est pas vide
                    texts.append(text)

        if not texts:
            logger.warning("No valid text inputs found for embedding generation")
            return []

        logger.info(f"Generating embeddings for {len(texts)} text inputs")
        try:
            return await self._make_request(texts, self.batch_size)
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            return []