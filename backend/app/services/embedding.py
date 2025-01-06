import logging
from typing import List, Dict, Any, Union
import voyageai
from PIL import Image
from ..core.config import settings

logger = logging.getLogger("technicia.embedding")

class EmbeddingService:
    def __init__(self):
        self.client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        self.batch_size = 20
        logger.info("Embedding service initialized")

    async def _make_request(self, input_groups: List[List[Union[str, Image.Image]]], batch_size: int = 20) -> List[List[float]]:
        try:
            all_embeddings = []
            
            # Traiter par lots
            for i in range(0, len(input_groups), batch_size):
                batch = input_groups[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(input_groups) + batch_size - 1)//batch_size}")
                
                try:
                    # Utiliser directement les groupes d'entrée
                    result = self.client.multimodal_embed(
                        inputs=batch,
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
            
    async def get_multimodal_embeddings(self, input_groups: List[List[Union[str, Image.Image]]]) -> List[List[float]]:
        """Génère des embeddings pour des groupes d'entrées multimodales.
        
        Args:
            input_groups: Liste de groupes, chaque groupe étant une liste contenant du texte et/ou des images PIL
        """
        if not input_groups:
            return []

        logger.info(f"Generating embeddings for {len(input_groups)} input groups")
        try:
            embeddings = await self._make_request(input_groups, self.batch_size)
            if not embeddings:
                logger.error("No embeddings generated from API response")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            return []