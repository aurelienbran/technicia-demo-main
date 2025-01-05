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
            # Extraction du contenu
            doc_content = await self._extract_pdf_content(file_path)
            if not doc_content:
                return False

            # Génération des embeddings et stockage
            embeddings = await self.embedding_service.get_multimodal_embeddings(doc_content)
            if not embeddings:
                return False

            # Stockage dans Qdrant
            metadata = self._generate_metadata(file_path, doc_content)
            await self.vector_store.store_vectors(embeddings, metadata)
            
            logger.info(f"PDF indexé avec succès: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'indexation du PDF {file_path}: {str(e)}")
            return False

    async def _extract_pdf_content(self, file_path: str) -> List[Dict[str, Any]]:
        try:
            content = []
            doc = fitz.open(file_path)

            # Extraction des images
            images = self.image_processor.extract_images_from_pdf(file_path)
            for img in images:
                content.append({
                    "image": img["image"],
                    "context": img["context"],
                    "page": img["page"],
                    "type": "image"
                })

            # Extraction et chunking intelligent du texte
            text_chunks = []
            current_section = ""
            current_context = ""

            for page in doc:
                # Récupération de la structure
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if block.get("type") == 0:  # Type 0 = text block
                        text = "".join([line["text"] for line in block["lines"]])
                        
                        # Détection des sections/titres
                        if len(text) < 100 and any(marker in text.lower() for marker in [". ", ":", "chapitre", "section"]):
                            if current_section:
                                text_chunks.extend(await self._smart_chunk_text(current_section, current_context))
                            current_context = text
                            current_section = ""
                        else:
                            current_section += text + " "

            # Traiter la dernière section
            if current_section:
                text_chunks.extend(await self._smart_chunk_text(current_section, current_context))

            # Ajouter les chunks de texte au contenu
            for chunk in text_chunks:
                content.append({
                    "text": chunk["text"],
                    "context": chunk["context"],
                    "type": "text"
                })

            return content
        except Exception as e:
            logger.error(f"Erreur extraction PDF {file_path}: {str(e)}")
            return []

    async def _smart_chunk_text(self, text: str, context: str) -> List[Dict[str, str]]:
        chunks = []
        text = text.strip()

        if len(text) <= self.chunk_size:
            return [{"text": text, "context": context}]

        start = 0
        while start < len(text):
            end = start + self.chunk_size

            # Ajuster aux limites naturelles
            if end < len(text):
                # Chercher la fin la plus appropriée
                markers = [". ", "\n\n", "\n", ". ", ": ", "; ", ", "]
                for marker in markers:
                    pos = text.rfind(marker, start, end)
                    if pos != -1:
                        end = pos + len(marker)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append({"text": chunk, "context": context})
            start = end - self.overlap

        return chunks

    def _generate_metadata(self, file_path: str, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        base_metadata = {
            "filename": os.path.basename(file_path),
            "path": file_path,
            "total_chunks": len(content)
        }

        metadata_list = []
        for idx, item in enumerate(content):
            metadata = base_metadata.copy()
            metadata.update({
                "chunk_index": idx,
                "type": item["type"],
                "context": item.get("context", ""),
                "page": item.get("page", 0) if item["type"] == "image" else 0
            })
            metadata_list.append(metadata)

        return metadata_list

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        try:
            query_embedding = await self.embedding_service.get_embedding_for_text(query)
            results = await self.vector_store.search_vectors(query_embedding, limit=limit)
            return results
        except Exception as e:
            logger.error(f"Error in search: {str(e)}")
            raise