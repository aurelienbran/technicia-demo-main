import os
import fitz
import shutil
import tempfile
import stat
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image
import io
from .vector_store import VectorStore
from .embedding import EmbeddingService

logger = logging.getLogger("technicia.indexing")

MAX_IMAGE_SIZE = (1920, 1080)

class IndexingService:
    def __init__(self):
        self.vector_store = VectorStore()
        self.embedding_service = EmbeddingService()
        self.chunk_size = 1000
        self.overlap = 200
        self.max_retries = 3
        self.retry_delay = 1

    async def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        try:
            query_embedding = await self.embedding_service.get_multimodal_embeddings([[query]])
            if not query_embedding or not query_embedding[0]:
                return {
                    "matches": [],
                    "error": "Failed to generate query embedding"
                }

            matches = await self.vector_store.search(
                query_vector=query_embedding[0],
                limit=limit
            )

            return {
                "matches": matches,
                "query": query
            }

        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return {
                "matches": [],
                "error": str(e)
            }

    def _resize_image_if_needed(self, image: Image.Image) -> Image.Image:
        if image.size[0] > MAX_IMAGE_SIZE[0] or image.size[1] > MAX_IMAGE_SIZE[1]:
            image.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
        return image

    def _extract_images_from_page(self, page) -> List[Tuple[Image.Image, str]]:
        images = []
        
        try:
            image_list = page.get_images(full=True)
            
            for img_index, img_info in enumerate(image_list):
                try:
                    base_image = page.parent.extract_image(img_info[0])
                    if base_image:
                        image_bytes = base_image["image"]
                        
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        pil_image = self._resize_image_if_needed(pil_image)
                        
                        rect = page.get_image_rects(img_info[0])[0]
                        extended_rect = fitz.Rect(
                            rect.x0 - 50,
                            rect.y0 - 50,
                            rect.x1 + 50,
                            rect.y1 + 50
                        )
                        surrounding_text = page.get_text("text", clip=extended_rect)
                        
                        if surrounding_text.strip():
                            images.append((pil_image, surrounding_text.strip()))
                        else:
                            images.append((pil_image, None))
                        
                except Exception as e:
                    logger.error(f"Error extracting specific image: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting images from page: {str(e)}")
        
        return images

    def _safe_read_file(self, file_path: str) -> Optional[bytes]:
        temp_path = None
        for attempt in range(self.max_retries):
            try:
                temp_dir = tempfile.mkdtemp()
                temp_path = os.path.join(temp_dir, f"temp_{os.path.basename(file_path)}")
                
                shutil.copy2(file_path, temp_path)
                
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
                if temp_path and os.path.exists(os.path.dirname(temp_path)):
                    try:
                        shutil.rmtree(os.path.dirname(temp_path))
                    except Exception as e:
                        logger.warning(f"Impossible de nettoyer le dossier temporaire: {str(e)}")

    async def index_pdf(self, file_path: str) -> bool:
        try:
            logger.info(f"Début indexation: {file_path}")
            
            pdf_bytes = self._safe_read_file(file_path)
            if pdf_bytes is None:
                logger.error("Impossible de lire le fichier PDF après plusieurs tentatives")
                return False

            logger.info(f"Lecture réussie: {len(pdf_bytes)} bytes")

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(doc)
            doc.close()
            logger.info(f"Test PDF OK: {page_count} pages")

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            contents = []

            for page_num in range(page_count):
                page = doc[page_num]
                
                text = page.get_text().strip()
                if text:
                    contents.append([text])
                
                page_images = self._extract_images_from_page(page)
                for img, context in page_images:
                    if context:
                        contents.append([img, context])
                    else:
                        contents.append([img])

            logger.info(f"Extraction réussie: {len(contents)} éléments")
            doc.close()

            if contents:
                embeddings = await self.embedding_service.get_multimodal_embeddings(contents)
                if embeddings:
                    metadata = [{
                        "filename": os.path.basename(file_path),
                        "page": idx // 2,
                        "content": content[0] if len(content) == 1 else context,
                        "type": "multimodal"
                    } for idx, (content, context) in enumerate(zip(contents, [None] * len(contents)))
                    ]
                    
                    success = await self.vector_store.store_vectors(embeddings, metadata)
                    if success:
                        logger.info(f"Indexation réussie")
                        return True
                    else:
                        logger.error("Echec du stockage des vecteurs")
                        return False

            logger.error("Aucun contenu extrait")
            return False

        except Exception as e:
            logger.error(f"Erreur indexation: {str(e)}")
            return False