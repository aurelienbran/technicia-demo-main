import logging
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Optional
import fitz  # PyMuPDF

logger = logging.getLogger("technicia.indexing")

class IndexingService:
    def __init__(self, embedding_service, vector_store, storage_service):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.storage_service = storage_service
        self.chunk_size = 1500
        self.chunk_overlap = 300

    def _get_file_hash(self, file_path: Path) -> str:
        try:
            stat_info = os.stat(file_path)
            file_info = f"{file_path}|{stat_info.st_size}|{stat_info.st_mtime}"
            return hashlib.sha256(file_info.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Erreur lors de la génération du hash: {str(e)}")
            raise

    def _extract_text_from_pdf(self, file_path: Path) -> List[Dict[str, any]]:
        try:
            # Utiliser le service de stockage pour lire le fichier
            pdf_content = self.storage_service.safe_read_file(file_path)
            if not pdf_content:
                raise IOError("Impossible de lire le fichier PDF")

            # Ouvrir le PDF depuis les données en mémoire
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            text_chunks = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                if not text.strip():
                    continue
                
                # Split text into chunks
                start = 0
                while start < len(text):
                    chunk = text[start:start + self.chunk_size]
                    if len(chunk.strip()) > 0:
                        text_chunks.append({
                            "text": chunk,
                            "page": page_num + 1,
                            "chunk_index": len(text_chunks)
                        })
                    start += self.chunk_size - self.chunk_overlap
            
            # Fermer le document
            doc.close()
            return text_chunks

        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du texte: {str(e)}")
            raise

    async def process_file(self, file_path: Path) -> bool:
        try:
            # Vérifier les permissions du fichier
            perms = self.storage_service.check_permissions(file_path)
            if not perms.get("exists") or not perms.get("is_file"):
                logger.error(f"Fichier non valide ou inaccessible: {file_path}")
                return False

            file_hash = self._get_file_hash(file_path)
            
            if self.vector_store.file_exists(str(file_path)):
                logger.info(f"Fichier {file_path} déjà indexé, ignoré")
                return True
            
            chunks = self._extract_text_from_pdf(file_path)
            if not chunks:
                logger.warning(f"Pas de texte extrait de {file_path}")
                return False
            
            texts = [chunk["text"] for chunk in chunks]
            metadatas = [
                {
                    "file_path": str(file_path),
                    "page": chunk["page"],
                    "chunk_index": chunk["chunk_index"],
                    "chunk_id": f"{file_hash}_{chunk['chunk_index']}"
                }
                for chunk in chunks
            ]
            
            embeddings = await self.embedding_service.get_embeddings(texts)
            if not embeddings:
                logger.error("Échec de la génération des embeddings")
                return False
            
            success = await self.vector_store.add_texts(texts, metadatas, embeddings)
            if success:
                logger.info(f"Indexation réussie de {file_path}")
                return True
            else:
                logger.error(f"Échec de l'ajout des vecteurs pour {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur inattendue: {str(e)}")
            return False