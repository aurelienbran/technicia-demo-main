import base64
import io
import fitz
import logging
from PIL import Image
from typing import List, Tuple, Dict

logger = logging.getLogger("technicia.image_processing")

class ImageProcessor:
    def __init__(self):
        self.max_pixels = 16000000  # 16M pixels limit for Voyage AI
        self.max_size_mb = 20  # 20MB limit
        
    def extract_images_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extrait les images d'un PDF avec leur contexte"""
        images = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Contexte de l'image
                        rect = page.get_image_bbox(img)
                        surrounding_text = page.get_text("text", clip=rect.expand(50))
                        
                        # Traitement et redimensionnement
                        processed_image = self._process_image(image_bytes)
                        if processed_image:
                            images.append({
                                "image": processed_image,
                                "context": surrounding_text.strip(),
                                "page": page_num + 1,
                                "position": img_index
                            })
                    except Exception as e:
                        logger.error(f"Erreur traitement image {img_index}, page {page_num}: {str(e)}")
                        continue
            return images
        except Exception as e:
            logger.error(f"Erreur extraction images PDF {pdf_path}: {str(e)}")
            return []

    def _process_image(self, image_bytes: bytes) -> str:
        """Traite et optimise une image pour Voyage AI"""
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # Convertir en RGB si nécessaire
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            
            # Vérifier et redimensionner si nécessaire
            w, h = img.size
            pixels = w * h
            if pixels > self.max_pixels:
                scale = (self.max_pixels / pixels) ** 0.5
                new_w = int(w * scale)
                new_h = int(h * scale)
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Convertir en Base64
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_b64 = base64.b64encode(buffered.getvalue()).decode()
            
            # Vérifier la taille finale
            if len(img_b64) > self.max_size_mb * 1024 * 1024:
                logger.warning(f"Image trop grande après optimisation: {len(img_b64) / (1024*1024):.2f}MB")
                return None
                
            return img_b64
        except Exception as e:
            logger.error(f"Erreur traitement image: {str(e)}")
            return None