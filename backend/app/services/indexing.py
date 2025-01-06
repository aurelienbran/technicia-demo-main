import os
import fitz
import shutil
import tempfile
import stat
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .vector_store import VectorStore
from .embedding import EmbeddingService

logger = logging.getLogger("technicia.indexing")

class IndexingService:
    def __init__(self):
        self.vector_store = VectorStore()
        self.embedding_service = EmbeddingService()
        self.chunk_size = 1000
        self.overlap = 200
        self.max_retries = 3
        self.retry_delay = 1

    def _extract_images_from_page(self, page) -> List[Dict[str, Any]]:
        """Extrait les images d'une page PDF avec leur contexte."""
        images = []
        
        try:
            # Extraire les images de la page
            image_list = page.get_images(full=True)
            
            for img_index, img_info in enumerate(image_list):
                try:
                    # Obtenir les données de l'image
                    base_image = page.parent.extract_image(img_info[0])
                    if base_image:
                        image_bytes = base_image["image"]
                        
                        # Récupérer le texte environnant comme contexte
                        # Utiliser img_info[0] pour les coordonnées de l'image
                        rect = page.get_image_rects(img_info[0])[0]  # Premier rectangle trouvé
                        surrounding_text = page.get_text("text", clip=rect.expand(50))  # 50 points autour de l'image
                        
                        images.append({
                            "type": "image",
                            "image": image_bytes,
                            "context": surrounding_text.strip() if surrounding_text else None
                        })
                        
                except Exception as e:
                    logger.error(f"Error extracting specific image: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting images from page: {str(e)}")
        
        return images

    def _safe_read_file(self, file_path: str) -> Optional[bytes]:
        """Lit un fichier de manière sécurisée avec plusieurs tentatives."""
        temp_path = None
        for attempt in range(self.max_retries):
            try:
                # Créer un dossier temporaire pour la copie
                temp_dir = tempfile.mkdtemp()
                temp_path = os.path.join(temp_dir, f"temp_{os.path.basename(file_path)}")
                
                # Copier le fichier
                shutil.copy2(file_path, temp_path)
                
                # Lire depuis la copie temporaire
                with open(temp_path, 'rb') as f:
                    return f.read()
                    
            except IOError as e:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Tentative {attempt + 1} échouée, nouvelle tentative dans {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Erreur persistante lors de la lecture: {str(e)}")
                    return None
            finally:
                # Nettoyer les fichiers temporaires
                if temp_path and os.path.exists(os.path.dirname(temp_path)):
                    try:
                        shutil.rmtree(os.path.dirname(temp_path))
                    except Exception as e:
                        logger.warning(f"Impossible de nettoyer le dossier temporaire: {str(e)}")

    async def index_pdf(self, file_path: str) -> bool:
        try:
            logger.info(f"Début indexation: {file_path}")
            
            # Lecture sécurisée du fichier avec plusieurs tentatives
            pdf_bytes = self._safe_read_file(file_path)
            if pdf_bytes is None:
                logger.error("Impossible de lire le fichier PDF après plusieurs tentatives")
                return False

            logger.info(f"Lecture réussie: {len(pdf_bytes)} bytes")

            # Test PyMuPDF avec bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(doc)
            doc.close()
            logger.info(f"Test PDF OK: {page_count} pages")

            # Extraction contenu
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            content = []

            # Extraction du texte et des images
            for page_num in range(page_count):
                page = doc[page_num]
                
                # Extraire le texte
                text = page.get_text()
                if text.strip():
                    content.append({"type": "text", "text": text})
                
                # Extraire les images
                page_images = self._extract_images_from_page(page)
                content.extend(page_images)

            logger.info(f"Extraction réussie: {len(content)} éléments")
            doc.close()

            if content:
                # Génération embeddings
                embeddings = await self.embedding_service.get_multimodal_embeddings(content)
                if embeddings:
                    # Stockage Qdrant
                    metadata = [{
                        "filename": os.path.basename(file_path),
                        "page": idx,
                        "type": "text" if idx < page_count else "image"
                    } for idx, _ in enumerate(embeddings)]
                    
                    await self.vector_store.add_texts(content, metadata, embeddings)
                    logger.info(f"Indexation réussie")
                    return True

            logger.error("Aucun contenu extrait")
            return False

        except Exception as e:
            logger.error(f"Erreur indexation: {str(e)}")
            return False