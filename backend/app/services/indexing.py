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
            logger.info(f"Début de l'indexation du PDF: {file_path}")
            
            # Vérification du fichier
            if not os.path.exists(file_path):
                logger.error(f"Fichier non trouvé: {file_path}")
                return False
                
            # Test de lecture du fichier
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                    logger.info(f"Lecture réussie: {len(data)} bytes")
            except Exception as e:
                logger.error(f"Erreur lecture fichier: {e}")
                return False

            # Test d'ouverture PDF
            try:
                doc = fitz.open(file_path)
                page_count = len(doc)
                doc.close()
                logger.info(f"Test PDF réussi: {page_count} pages")
            except Exception as e:
                logger.error(f"Échec test PDF: {str(e)}")
                return False

            # Extraction contenu
            doc_content = await self._extract_pdf_content(file_path)
            if not doc_content:
                logger.error("Aucun contenu extrait")
                return False

            # Embeddings
            embeddings = await self.embedding_service.get_multimodal_embeddings(doc_content)
            if not embeddings:
                logger.error("Échec génération embeddings")
                return False

            # Stockage Qdrant
            metadata = self._generate_metadata(file_path, doc_content)
            await self.vector_store.store_vectors(embeddings, metadata)
            
            logger.info(f"Indexation réussie: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur indexation: {str(e)}", exc_info=True)
            return False