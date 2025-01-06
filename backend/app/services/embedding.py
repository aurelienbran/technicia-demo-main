import logging
import base64
from typing import List, Dict, Any
import voyageai
from PIL import Image
import io
from ..core.config import settings

logger = logging.getLogger("technicia.embedding")

class EmbeddingService:
    def __init__(self):
        self.client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        self.batch_size = 20
        logger.info("Embedding service initialized")

    def _convert_image_to_pil(self, image_bytes: bytes) -> Image.Image:
        """Convertit des bytes d'image en objet PIL.Image."""
        try:
            return Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            logger.error(f"Error converting image bytes to PIL: {str(e)}")
            raise

    async def _make_request(self, contents: List[List[Dict[str, Any]]], batch_size: int = 20) -> List[List[float]]:
        try:
            all_embeddings = []
            
            # Traiter par lots
            for i in range(0, len(contents), batch_size):
                batch = contents[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(contents) + batch_size - 1)//batch_size}")
                
                try:
                    # Utiliser l'API voyageai pour les embeddings multimodaux
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
            
    async def get_multimodal_embeddings(self, documents: List[Dict[str, Any]]) -> List[List[float]]:
        """Génère des embeddings pour des documents texte et images."""
        if not documents:
            return []
            
        # Préparer les contenus multimodaux
        contents = []
        current_content = []
        
        for doc in documents:
            if doc["type"] == "text" and "text" in doc:
                # Si on a déjà du contenu, on le sauvegarde
                if current_content:
                    contents.append(current_content)
                    current_content = []
                
                text = doc["text"].strip()
                if text:  # Vérifier que le texte n'est pas vide
                    current_content = [{"text": text}]
                    contents.append(current_content)
                    current_content = []
                    
            elif doc["type"] == "image" and "image" in doc:
                try:
                    # Convertir l'image en PIL.Image
                    pil_image = self._convert_image_to_pil(doc["image"])
                    current_content.append(pil_image)
                    
                    # Ajouter le contexte si disponible
                    if "context" in doc:
                        current_content.append(doc["context"])
                        
                except Exception as e:
                    logger.error(f"Error processing image: {str(e)}")
                    continue

        # Ajouter le dernier contenu s'il existe
        if current_content:
            contents.append(current_content)

        if not contents:
            logger.warning("No valid inputs found for embedding generation")
            return []

        logger.info(f"Generating embeddings for {len(contents)} content groups")
        try:
            embeddings = await self._make_request(contents, self.batch_size)
            if not embeddings:
                logger.error("No embeddings generated from API response")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            return []