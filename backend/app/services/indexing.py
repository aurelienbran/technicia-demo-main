import os
import fitz
import shutil
import tempfile
import stat
import logging
import win32file
import win32security
from pathlib import Path
from typing import List, Dict, Any, Optional
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

    def _safe_read_file(self, file_path: str) -> Optional[bytes]:
        """Lit un fichier de manière sécurisée en utilisant l'API Windows."""
        try:
            # Obtenir un handle sécurisé au fichier
            handle = win32file.CreateFile(
                file_path,
                win32file.GENERIC_READ,
                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE,
                None,
                win32file.OPEN_EXISTING,
                win32file.FILE_ATTRIBUTE_NORMAL,
                None
            )

            try:
                # Lire le contenu du fichier
                data = bytearray()
                while True:
                    hr, chunk = win32file.ReadFile(handle, 8192)
                    if not chunk:
                        break
                    data.extend(chunk)
                return bytes(data)
            finally:
                handle.Close()

        except Exception as e:
            logger.error(f"Erreur lors de la lecture du fichier {file_path}: {str(e)}")
            return None

    async def index_pdf(self, file_path: str) -> bool:
        try:
            logger.info(f"Début indexation: {file_path}")
            
            # Lecture sécurisée du fichier
            pdf_bytes = self._safe_read_file(file_path)
            if pdf_bytes is None:
                logger.error("Impossible de lire le fichier PDF")
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
            logger.error(f"Erreur indexation: {str(e)}")
            return False