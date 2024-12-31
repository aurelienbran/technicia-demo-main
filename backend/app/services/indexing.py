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
        logger.info("Indexing service initialized")

    async def index_document(self, file_path: str) -> Dict:
        """
        Indexe un document PDF en utilisant un générateur pour réduire l'utilisation de la mémoire.
        """
        try:
            metadata = await self._get_pdf_metadata(file_path)
            chunks_processed = 0
            
            async for chunk, page_num in self._stream_pdf_chunks(file_path):
                try:
                    if not chunk.strip():  # Skip empty chunks
                        continue

                    # Vérifier si le chunk est déjà indexé
                    chunk_hash = self._generate_hash(chunk)
                    if await self._is_chunk_indexed(chunk_hash):
                        logger.debug(f"Chunk already indexed, skipping: {chunk_hash}")
                        continue

                    # Générer l'embedding pour le chunk
                    embedding = await self.embedding.get_embedding(chunk)
                    
                    # Préparer le payload
                    payload = {
                        **metadata,
                        "page_number": page_num,
                        "chunk_index": chunks_processed,
                        "text": chunk,
                        "chunk_hash": chunk_hash,
                        "indexed_at": datetime.utcnow().isoformat()
                    }
                    
                    # Stocker dans Qdrant
                    await self.vector_store.add_vectors(
                        vectors=[embedding],
                        payloads=[payload]
                    )
                    
                    chunks_processed += 1
                    logger.debug(f"Processed chunk {chunks_processed} from page {page_num}")
                    
                    # Rate limiting
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {chunks_processed} of {file_path}: {str(e)}")
                    continue

            logger.info(f"Successfully indexed {file_path}: {chunks_processed} chunks processed")
            return {
                "status": "success",
                "file": file_path,
                "chunks_processed": chunks_processed,
                "metadata": metadata,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error indexing document {file_path}: {str(e)}")
            return {
                "status": "error",
                "file": file_path,
                "error": str(e),
                "chunks_processed": 0,
                "metadata": {}
            }

    async def _get_pdf_metadata(self, file_path: str) -> Dict:
        """
        Extrait uniquement les métadonnées d'un PDF.
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
            doc.close()
            return metadata
        except Exception as e:
            logger.error(f"Error getting PDF metadata for {file_path}: {str(e)}")
            raise

    async def _is_chunk_indexed(self, chunk_hash: str) -> bool:
        """
        Vérifie si un chunk est déjà indexé dans Qdrant.
        """
        try:
            results = await self.vector_store.search_by_hash(chunk_hash)
            return len(results) > 0
        except Exception as e:
            logger.error(f"Error checking chunk hash {chunk_hash}: {str(e)}")
            return False

    async def _stream_pdf_chunks(self, file_path: str) -> AsyncGenerator[tuple[str, int], None]:
        """
        Génère les chunks de texte d'un PDF de manière asynchrone et efficace.
        """
        doc = None
        try:
            doc = fitz.open(file_path)
            text_buffer = ""
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                
                if not page_text.strip():
                    continue
                    
                text_buffer += page_text + " "
                
                # Process text_buffer into chunks
                while len(text_buffer) >= self.chunk_size:
                    # Find a good breakpoint
                    breakpoint = text_buffer[:self.chunk_size].rfind(". ")
                    if breakpoint == -1:
                        breakpoint = text_buffer[:self.chunk_size].rfind(" ")
                    if breakpoint == -1:
                        breakpoint = self.chunk_size
                    
                    chunk = text_buffer[:breakpoint].strip()
                    if chunk:  # Only yield non-empty chunks
                        yield chunk, page_num + 1
                    
                    # Keep overlap for next chunk
                    text_buffer = text_buffer[max(0, breakpoint - self.chunk_overlap):]
            
            # Don't forget the last chunk
            if text_buffer.strip():
                yield text_buffer.strip(), page_num + 1
                
        except Exception as e:
            logger.error(f"Error streaming PDF {file_path}: {str(e)}")
            raise
        finally:
            if doc:
                doc.close()

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
        Recherche dans les documents indexés de manière optimisée.
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

            # Extraire et filtrer les contextes pertinents
            contexts = []
            seen_hashes = set()
            
            for result in results:
                chunk_hash = result["payload"].get("chunk_hash")
                if chunk_hash and chunk_hash not in seen_hashes:
                    contexts.append(result["payload"]["text"])
                    seen_hashes.add(chunk_hash)

            # Obtenir une réponse de Claude avec le contexte optimisé
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