import logging
import asyncio
from typing import List, Dict
from datetime import datetime
from pathlib import Path
import hashlib
import fitz
import numpy as np
from fitz.fitz import FileDataError
import os

from .claude import ClaudeService
from .embedding import EmbeddingService
from .vector_store import VectorStore
from .image_processing import ImageProcessor
from ..core.config import settings

logger = logging.getLogger("technicia.indexing")

class IndexingService:
    def __init__(self):
        self.claude = ClaudeService()
        self.embedding = EmbeddingService()
        self.vector_store = VectorStore()
        self.image_processor = ImageProcessor()

    async def index_document(self, file_path: str) -> Dict:
        try:
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                logger.error(error_msg)
                return {"status": "error", "error": error_msg}

            file_hash = self._get_file_hash(file_path)
            doc = None

            try:
                doc = fitz.open(file_path)
                metadata = self._get_document_metadata(doc, file_path, file_hash)
                
                # Traitement parallèle du texte et des images
                text_chunks = []
                image_chunks = []

                for page_num in range(len(doc)):
                    page = doc[page_num]
                    
                    # Extraction du texte
                    text = page.get_text()
                    if text.strip():
                        text_chunks.extend(self._split_text(text, page_num + 1))
                    
                    # Extraction et traitement des images
                    images = await self.image_processor.extract_images_from_pdf(page)
                    for img_data in images:
                        image_context = self._prepare_image_context(
                            img_data, metadata, page_num + 1
                        )
                        image_chunks.append(image_context)

                logger.info(f"Extracted {len(text_chunks)} text chunks and {len(image_chunks)} images from {file_path}")

                if not text_chunks and not image_chunks:
                    return {"status": "error", "error": "No content found in document"}

                # Indexation du texte
                await self._index_text_chunks(text_chunks, metadata)

                # Indexation des images
                await self._index_image_chunks(image_chunks, metadata)

                return {
                    "status": "success",
                    "file": file_path,
                    "text_chunks": len(text_chunks),
                    "image_chunks": len(image_chunks)
                }

            except Exception as e:
                logger.error(f"Error processing document: {str(e)}")
                return {"status": "error", "error": str(e)}
            finally:
                if doc:
                    doc.close()

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"status": "error", "error": str(e)}

    def _prepare_image_context(self, img_data: Dict, metadata: Dict, page_num: int) -> Dict:
        """Prépare le contexte d'une image pour l'indexation."""
        context_text = f"Type: {img_data['type']}\n"
        if img_data['context']:
            context_text += f"Context: {img_data['context']}\n"
        context_text += f"Location: Page {page_num}, Position: {img_data['position']}"

        return {
            **metadata,
            "page_number": page_num,
            "content_type": "image",
            "image_type": img_data['type'],
            "text": context_text,
            "image_data": img_data['image_data'],
            "position": img_data['position']
        }

    async def _index_text_chunks(self, chunks: List[tuple[str, int]], metadata: Dict):
        """Indexe les chunks de texte."""
        for i, (chunk, page_num) in enumerate(chunks):
            try:
                embedding = await self.embedding.get_embedding(chunk)
                payload = {
                    **metadata,
                    "page_number": page_num,
                    "chunk_index": i,
                    "content_type": "text",
                    "text": chunk,
                }
                await self.vector_store.add_vectors([embedding], [payload])
            except Exception as e:
                logger.error(f"Error indexing text chunk {i}: {str(e)}")

    async def _index_image_chunks(self, chunks: List[Dict], metadata: Dict):
        """Indexe les chunks d'images avec leur contexte."""
        for i, chunk in enumerate(chunks):
            try:
                # Utilisation du texte de contexte pour l'embedding
                context_embedding = await self.embedding.get_embedding(chunk['text'])
                
                # TODO: Ajouter l'embedding de l'image elle-même quand disponible
                # image_embedding = await self.get_image_embedding(chunk['image_data'])
                # final_embedding = self.combine_embeddings(context_embedding, image_embedding)
                
                await self.vector_store.add_vectors([context_embedding], [chunk])
            except Exception as e:
                logger.error(f"Error indexing image chunk {i}: {str(e)}")

    def _get_document_metadata(self, doc: fitz.Document, file_path: str, file_hash: str) -> Dict:
        return {
            "filename": Path(file_path).name,
            "title": doc.metadata.get("title", ""),
            "author": doc.metadata.get("author", ""),
            "doc_type": "pdf",
            "page_count": len(doc),
            "file_path": file_path,
            "file_hash": file_hash,
            "indexed_at": datetime.utcnow().isoformat()
        }

    # [Le reste du code existant reste inchangé]