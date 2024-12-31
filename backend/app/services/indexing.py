from typing import List, Dict, Generator, AsyncGenerator
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
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP
        self.rate_limit_delay = 0.1  # 100ms entre les requêtes
        self._processed_chunks = set()  # Cache local des chunks traités
        logger.info("Indexing service initialized")

    async def index_document(self, file_path: str) -> Dict:
        """
        Indexe un document PDF.
        """
        try:
            doc = fitz.open(file_path)
            metadata = {
                "filename": Path(file_path).name,
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "doc_type": "pdf",
                "page_count": len(doc),
                "file_path": file_path,
            }

            # Récupérer tout le texte du document
            full_text = ""
            for page in doc:
                full_text += page.get_text() + "\n"
            doc.close()

            # Découper en chunks avec chevauchement
            chunks = []
            current_pos = 0
            while current_pos < len(full_text):
                # Trouver une bonne fin de chunk
                end_pos = min(current_pos + self.chunk_size, len(full_text))
                if end_pos < len(full_text):
                    # Chercher la dernière phrase complète
                    last_period = full_text.rfind(".", current_pos, end_pos)
                    if last_period != -1:
                        end_pos = last_period + 1

                chunk = full_text[current_pos:end_pos].strip()
                if chunk:  # Ignorer les chunks vides
                    chunks.append(chunk)
                current_pos = end_pos - self.chunk_overlap

            # Indexer les chunks
            chunks_processed = 0
            for chunk in chunks:
                try:
                    chunk_hash = self._generate_hash(chunk)
                    if chunk_hash in self._processed_chunks:
                        continue

                    # Générer l'embedding
                    embedding = await self.embedding.get_embedding(chunk)
                    
                    # Stocker dans Qdrant
                    await self.vector_store.add_vectors(
                        vectors=[embedding],
                        payloads=[{
                            **metadata,
                            "chunk_index": chunks_processed,
                            "text": chunk,
                            "chunk_hash": chunk_hash,
                            "indexed_at": datetime.utcnow().isoformat()
                        }]
                    )
                    
                    self._processed_chunks.add(chunk_hash)
                    chunks_processed += 1
                    
                    # Rate limiting
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {chunks_processed}: {str(e)}")
                    continue

            logger.info(f"Successfully indexed {file_path}: {chunks_processed} chunks processed")
            return {
                "status": "success",
                "file": file_path,
                "chunks_processed": chunks_processed,
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Error indexing document {file_path}: {str(e)}")
            return {
                "status": "error",
                "file": file_path,
                "error": str(e),
                "chunks_processed": 0
            }

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

            # Préparer le contexte pour Claude
            contexts = [r["payload"]["text"] for r in results]
            context_text = "\n---\n".join(contexts)

            # Obtenir une réponse de Claude
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