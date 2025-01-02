import logging
import fitz
import io
from PIL import Image
import numpy as np
from typing import List, Dict, Tuple, Optional
from ..core.config import settings

logger = logging.getLogger("technicia.image_processing")

class ImageProcessor:
    def __init__(self):
        self.min_image_size = 100  # Taille minimale en pixels
        self.max_image_size = 1024  # Taille maximale en pixels

    async def extract_images_from_pdf(self, page: fitz.Page) -> List[Dict]:
        """Extrait et traite les images d'une page PDF."""
        try:
            images = []
            image_list = page.get_images(full=True)

            for img_index, img_info in enumerate(image_list):
                try:
                    # Extraction de l'image
                    base_image = page.parent.extract_image(img_info[0])
                    if not base_image:
                        continue

                    # Conversion en format PIL
                    image_data = base_image["image"]
                    image = Image.open(io.BytesIO(image_data))

                    # Vérification de la taille minimale
                    if image.width < self.min_image_size or image.height < self.min_image_size:
                        continue

                    # Redimensionnement si nécessaire
                    if image.width > self.max_image_size or image.height > self.max_image_size:
                        image = self.resize_image(image)

                    # Extraction des informations de position
                    bbox = page.get_image_bbox(img_info[0])
                    
                    # Analyse du contexte autour de l'image
                    surrounding_text = self.get_surrounding_text(page, bbox)

                    # Préparation des métadonnées
                    image_metadata = {
                        "page_number": page.number + 1,
                        "position": {
                            "x": bbox.x0,
                            "y": bbox.y0,
                            "width": bbox.width,
                            "height": bbox.height
                        },
                        "context": surrounding_text,
                        "type": self.determine_image_type(image, surrounding_text),
                        "image_data": image
                    }

                    images.append(image_metadata)

                except Exception as e:
                    logger.warning(f"Error processing image {img_index} on page {page.number + 1}: {str(e)}")
                    continue

            return images

        except Exception as e:
            logger.error(f"Error extracting images from page {page.number + 1}: {str(e)}")
            return []

    def resize_image(self, image: Image.Image) -> Image.Image:
        """Redimensionne l'image en conservant les proportions."""
        ratio = min(self.max_image_size / max(image.size))
        new_size = tuple(int(dim * ratio) for dim in image.size)
        return image.resize(new_size, Image.Resampling.LANCZOS)

    def get_surrounding_text(self, page: fitz.Page, bbox: fitz.Rect, margin: int = 50) -> str:
        """Extrait le texte autour d'une image."""
        try:
            # Étendre la zone de recherche
            search_rect = fitz.Rect(
                bbox.x0 - margin,
                bbox.y0 - margin,
                bbox.x1 + margin,
                bbox.y1 + margin
            )
            return page.get_text("text", clip=search_rect).strip()
        except Exception as e:
            logger.warning(f"Error getting surrounding text: {str(e)}")
            return ""

    def determine_image_type(self, image: Image.Image, context: str) -> str:
        """Détermine le type d'image (schéma, diagramme, photo, etc.)."""
        # Analyse des caractéristiques de l'image
        is_bw = self.is_black_and_white(image)
        has_straight_lines = self.detect_straight_lines(image)
        text_indicators = ["schéma", "diagramme", "circuit", "plan"] 
        
        # Décision basée sur les caractéristiques
        if is_bw and has_straight_lines:
            if any(indicator in context.lower() for indicator in text_indicators):
                return "schema_technique"
            return "diagram"
        return "photo"

    def is_black_and_white(self, image: Image.Image) -> bool:
        """Détecte si l'image est principalement en noir et blanc."""
        try:
            gray = image.convert('L')
            extrema = gray.getextrema()
            return extrema[1] - extrema[0] < 200  # Seuil pour N&B
        except Exception:
            return False

    def detect_straight_lines(self, image: Image.Image) -> bool:
        """Détecte la présence de lignes droites (indicateur de schéma technique)."""
        try:
            # Conversion en niveaux de gris et détection basique des contours
            gray = np.array(image.convert('L'))
            edges = np.gradient(gray)
            return np.std(edges) > 20  # Seuil arbitraire pour la détection
        except Exception:
            return False