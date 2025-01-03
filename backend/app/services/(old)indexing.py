from typing import List, Dict, Optional
import logging
import asyncio
import fitz  # PyMuPDF
import hashlib
from pathlib import Path
from datetime import datetime

from .claude import ClaudeService
from .embedding import EmbeddingService
from .vector_store import VectorStore
from ..core.config import settings

logger = logging.getLogger("technicia.indexing")

class IndexingService:
    def __init__(self):
        self.claude = ClaudeService()
        self.embedding = EmbeddingService()
        self.vector_store = VectorStore()
        logger.info("Indexing service initialized")

    async def index_document(self, file_path: str) -> Dict:
        """
        Indexe un document PDF.
        """
        try:
            # Extraire le texte et les métadonnées
            text_chunks, metadata = await self._process_pdf(file_path)
            logger.info(f"Processed PDF: {file_path}, generated {len(text_chunks)} chunks")

            # Générer les embeddings pour chaque chunk
            embeddings = await self.embedding.get_embeddings(text_chunks)

            # Préparer les payloads pour chaque chunk
            payloads = []
            for i, chunk in enumerate(text_chunks):
                payload = {
                    **metadata,
                    "chunk_index": i,
                    "text": chunk,
                    "chunk_hash": self._generate_hash(chunk),
                    "indexed_at": datetime.utcnow().isoformat()
                }
                payloads.append(payload)

            # Stocker dans Qdrant
            await self.vector_store.add_vectors(
                vectors=embeddings,
                payloads=payloads
            )

            return {
                "status": "success",
                "file": file_path,
                "chunks_processed": len(text_chunks),
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Error indexing document {file_path}: {str(e)}")
            raise

    async def _process_pdf(self, file_path: str) -> tuple[List[str], Dict]:
        """
        Extrait le texte et les métadonnées d'un PDF.
        """
        try:
            doc = fitz.open(file_path)
            
            # Extraire les métadonnées
            metadata = {
                "filename": Path(file_path).name,
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "doc_type": "pdf",
                "page_count": len(doc),
                "file_path": file_path,
            }

            # Extraire et prétraiter le texte
            text_chunks = []
            for page in doc:
                text = page.get_text()
                if text.strip():  # Ignorer les pages vides
                    # Prétraiter et découper le texte en chunks
                    processed_text = await self.embedding.preprocess_text(text)
                    chunks = await self.embedding.chunk_text(processed_text)
                    text_chunks.extend(chunks)

            return text_chunks, metadata

        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {str(e)}")
            raise

    async def index_directory(self, directory_path: str) -> List[Dict]:
        """
        Indexe tous les PDFs dans un répertoire.
        """
        try:
            pdf_files = list(Path(directory_path).glob("**/*.pdf"))
            logger.info(f"Found {len(pdf_files)} PDF files in {directory_path}")

            results = []
            for pdf_file in pdf_files:
                try:
                    result = await self.index_document(str(pdf_file))
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to index {pdf_file}: {str(e)}")
                    results.append({
                        "status": "error",
                        "file": str(pdf_file),
                        "error": str(e)
                    })

            return results

        except Exception as e:
            logger.error(f"Error indexing directory {directory_path}: {str(e)}")
            raise

    @staticmethod
    def _generate_hash(text: str) -> str:
        """
        Génère un hash unique pour un texte.
        """
        return hashlib.md5(text.encode()).hexdigest()

    async def search(
        self, 
        query: str, 
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> Dict:
        """
        Recherche dans les documents indexés.
        """
        try:
            # Générer l'embedding pour la requête
            query_embedding = await self.embedding.get_embedding(query)

            # Rechercher dans Qdrant
            results = await self.vector_store.search(
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )

            # Extraire les contextes pertinents
            contexts = [result["payload"]["text"] for result in results]
            
            # Obtenir une réponse de Claude avec le contexte
            context_text = "\n---\n".join(contexts)
            answer = await self.claude.get_response(
                query=query,
                context=context_text
            )

            return {
                "answer": answer,
                "sources": results,
                "context_used": len(contexts)
            }

        except Exception as e:
            logger.error(f"Error searching: {str(e)}")
            raise