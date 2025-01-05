import os
import fitz
import logging
from typing import List, Dict, Any
from .vector_store import VectorStore
from .embedding import EmbeddingService
from .image_processing import ImageProcessor

logger = logging.getLogger("technicia.indexing")

class IndexingService:
    def __init__(self):
        self.vector_store = VectorStore()
        self.embedding_service = EmbeddingService()
        self.image_processor = ImageProcessor()
        self.chunk_size = 1000
        self.overlap = 200

    async def index_pdf(self, file_path: str) -> bool:
        try:
            logger.info(f"Début indexation: {file_path}")
            try:
                # Test ouverture en mode binaire
                pdf_bytes = None
                try:
                    with open(file_path, 'rb') as file:
                        pdf_bytes = file.read()
                    logger.info(f"Lecture réussie: {len(pdf_bytes)} bytes")
                except IOError as e:
                    logger.error(f"Erreur IO: {str(e)}")
                    logger.error(f"Permissions fichier: {oct(os.stat(file_path).st_mode & 0o777)}")
                    raise

                # Test PyMuPDF avec bytes
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                page_count = len(doc)
                doc.close()
                logger.info(f"Test PDF OK: {page_count} pages")

                # Extraction contenu
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                content = []

                # Extraction du texte
                for page_num in range(page_count):
                    page = doc[page_num]
                    text = page.get_text()
                    if text.strip():
                        content.append({"text": text, "type": "text"})

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
                            "type": "text"
                        } for idx, _ in enumerate(embeddings)]
                        
                        await self.vector_store.store_vectors(embeddings, metadata)
                        logger.info(f"Indexation réussie")
                        return True

                logger.error("Aucun contenu extrait")
                return False

            except Exception as e:
                logger.error(f"Erreur traitement PDF: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Erreur indexation: {str(e)}")
            return False