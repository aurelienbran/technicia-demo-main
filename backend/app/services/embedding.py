import logging
from typing import List, Dict, Any
import voyageai
from ..core.config import settings

logger = logging.getLogger("technicia.embedding")

class EmbeddingService:
    def __init__(self):
        self.client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        self.batch_size = 20
        logger.info("Embedding service initialized")

    async def _make_request(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        try:
            all_embeddings = []
            
            # Traiter par lots
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
                
                try:
                    # Utiliser l'API voyageai directement
                    result = self.client.multimodal_embed(
                        inputs=[[
                            text  # Les textes simples sont automatiquement convertis
                        ] for text in batch],
                        model="voyage-multimodal-3",
                        input_type="document"
                    )
                    
                    all_embeddings.extend(result.embeddings)
                    
                    # Log des tokens utilisés
                    logger.info(
                        f"Usage - Text tokens: {result.text_tokens}, "
                        f"Image pixels: {result.image_pixels}, "
                        f"Total tokens: {result.total_tokens}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error during API call: {str(e)}")
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
            embeddings = await self._make_request(texts, self.batch_size)
            if not embeddings:
                logger.error("No embeddings generated from API response")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            return []