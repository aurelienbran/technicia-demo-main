import logging
import asyncio
from typing import List, Dict, AsyncGenerator
from datetime import datetime
from pathlib import Path
import hashlib
import fitz

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
        self.rate_limit_delay = 0.1
        self._processed_hashes = set()  # Cache local des hashes
        logger.info("Indexing service initialized")

    async def index_document(self, file_path: str) -> Dict:
        """Index et traite un document PDF."""
        try:
            metadata = await self._get_pdf_metadata(file_path)
            chunks_processed = 0
            
            async for chunk, page_num in self._stream_pdf_chunks(file_path):
                try:
                    # Vérifier si le chunk est déjà traité
                    chunk_hash = self._generate_hash(chunk)
                    if chunk_hash in self._processed_hashes:
                        logger.debug(f"Chunk already processed, skipping: {chunk_hash}")
                        continue

                    # Générer l'embedding
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
                    
                    self._processed_hashes.add(chunk_hash)
                    chunks_processed += 1
                    logger.debug(f"Processed chunk {chunks_processed} from page {page_num}")
                    
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

    async def search(self, query: str, limit: int = 5) -> Dict:
        """Recherche dans les documents indexés et génère une réponse."""
        try:
            # Générer l'embedding pour la requête
            query_embedding = await self.embedding.get_embedding(query)

            # Rechercher dans Qdrant
            results = await self.vector_store.search(
                query_vector=query_embedding,
                limit=limit,
                score_threshold=0.0
            )

            # Préparer le contexte pour Claude
            if results:
                # Extraire et déduplicate les textes
                texts = []
                unique_hashes = set()
                for result in results:
                    chunk_hash = result["payload"].get("chunk_hash")
                    if chunk_hash and chunk_hash not in unique_hashes:
                        text = result["payload"].get("text", "").strip()
                        if text:
                            texts.append(text)
                            unique_hashes.add(chunk_hash)

                # Former le contexte
                if texts:
                    context = "\n---\n".join(texts)
                    prompt = f"Analyze and summarize this technical content. First understand what the document is about, then focus on answering this question: {query}\n\nContent to analyze:\n{context}"
                    
                    # Générer la réponse
                    answer = await self.claude.get_response(prompt)
                    
                    return {
                        "answer": answer,
                        "sources": results
                    }

            return {
                "answer": "Je ne trouve pas d'information pertinente pour répondre à cette question dans les documents fournis.",
                "sources": []
            }

        except Exception as e:
            logger.error(f"Error searching: {str(e)}")
            raise

    async def _get_pdf_metadata(self, file_path: str) -> Dict:
        """Extrait les métadonnées d'un PDF."""
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
            logger.error(f"Error getting PDF metadata: {str(e)}")
            raise

    async def _stream_pdf_chunks(self, file_path: str) -> AsyncGenerator[tuple[str, int], None]:
        """Génère les chunks de texte d'un PDF."""
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
                
                while len(text_buffer) >= settings.CHUNK_SIZE:
                    # Trouver un point de coupure naturel
                    breakpoint = text_buffer[:settings.CHUNK_SIZE].rfind(". ")
                    if breakpoint == -1:
                        breakpoint = text_buffer[:settings.CHUNK_SIZE].rfind(" ")
                    if breakpoint == -1:
                        breakpoint = settings.CHUNK_SIZE
                    
                    chunk = text_buffer[:breakpoint].strip()
                    if chunk:  # Ne pas retourner les chunks vides
                        yield chunk, page_num + 1
                    
                    # Garder le chevauchement pour le prochain chunk
                    text_buffer = text_buffer[max(0, breakpoint - settings.CHUNK_OVERLAP):]
            
            # Traiter le dernier chunk
            if text_buffer.strip():
                yield text_buffer.strip(), len(doc)
                
        except Exception as e:
            logger.error(f"Error streaming PDF: {str(e)}")
            raise
        finally:
            if doc:
                doc.close()

    @staticmethod
    def _generate_hash(text: str) -> str:
        """Génère un hash unique pour un texte."""
        return hashlib.md5(text.encode()).hexdigest()