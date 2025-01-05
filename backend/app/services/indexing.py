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
            logger.debug(f"Vérification du fichier...")
            if not os.path.exists(file_path):
                logger.error(f"Fichier non trouvé: {file_path}")
                return False
                
            # Test d'ouverture du PDF
            try:
                doc = fitz.open(file_path)
                doc.close()
                logger.info(f"Test d'ouverture PDF réussi")
            except Exception as e:
                logger.error(f"Échec du test d'ouverture PDF: {str(e)}")
                return False

            # Extraction du contenu
            logger.info("Début extraction contenu...")
            doc_content = await self._extract_pdf_content(file_path)
            if not doc_content:
                logger.error("Aucun contenu extrait du PDF")
                return False

            # Génération des embeddings
            logger.info(f"Génération des embeddings pour {len(doc_content)} éléments")
            embeddings = await self.embedding_service.get_multimodal_embeddings(doc_content)
            if not embeddings:
                logger.error("Échec de la génération des embeddings")
                return False

            # Stockage Qdrant
            logger.info("Stockage dans Qdrant...")
            metadata = self._generate_metadata(file_path, doc_content)
            await self.vector_store.store_vectors(embeddings, metadata)
            
            logger.info(f"PDF indexé avec succès: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'indexation du PDF {file_path}: {str(e)}", exc_info=True)
            return False

    async def _extract_pdf_content(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Début extraction PDF: {file_path}")
            content = []
            doc = fitz.open(file_path)
            logger.info(f"PDF ouvert: {len(doc)} pages")

            # Extraction des images
            logger.info("Extraction des images...")
            images = self.image_processor.extract_images_from_pdf(file_path)
            logger.info(f"Images extraites: {len(images)}")
            for img in images:
                content.append({
                    "image": img["image"],
                    "context": img["context"],
                    "page": img["page"],
                    "type": "image"
                })

            # Extraction du texte
            logger.info("Extraction du texte...")
            text_chunks = []
            current_section = ""
            current_context = ""

            for page_num in range(len(doc)):
                logger.debug(f"Traitement page {page_num + 1}/{len(doc)}")
                page = doc[page_num]
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if block.get("type") == 0:  # Type 0 = text block
                        lines = block.get("lines", [])
                        if not lines:
                            logger.debug(f"Bloc sans lignes trouvé page {page_num + 1}")
                            continue
                            
                        text = "".join([line.get("text", "") for line in lines])
                        
                        if len(text) < 100 and any(marker in text.lower() for marker in [". ", ":", "chapitre", "section"]):
                            if current_section:
                                text_chunks.extend(await self._smart_chunk_text(current_section, current_context))
                            current_context = text
                            current_section = ""
                        else:
                            current_section += text + " "

            if current_section:
                text_chunks.extend(await self._smart_chunk_text(current_section, current_context))

            logger.info(f"Chunks texte créés: {len(text_chunks)}")
            for chunk in text_chunks:
                content.append({
                    "text": chunk["text"],
                    "context": chunk["context"],
                    "type": "text"
                })

            logger.info(f"Extraction terminée: {len(content)} éléments au total")
            return content
        except Exception as e:
            logger.error(f"Erreur extraction PDF {file_path}: {str(e)}", exc_info=True)
            return []