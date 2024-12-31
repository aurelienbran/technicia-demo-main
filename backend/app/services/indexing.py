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
        doc = None
        try:
            logger.info(f"Opening document: {file_path}")
            doc = fitz.open(file_path)
            
            # Extraire les métadonnées
            metadata = {
                "filename": Path(file_path).name,
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "doc_type": "pdf",
                "page_count": len(doc),
                "file_path": str(file_path),
            }
            logger.info(f"Document metadata: {metadata}")

            # Traiter le document page par page
            chunks_processed = 0
            for page_num in range(len(doc)):
                try:
                    page = doc[page_num]
                    page_text = page.get_text()
                    
                    # Découper le texte en chunks
                    text_chunks = self._split_text(page_text)
                    logger.debug(f"Page {page_num + 1}: {len(text_chunks)} chunks")
                    
                    for chunk in text_chunks:
                        if not chunk.strip():
                            continue
                            
                        # Générer le hash et vérifier si déjà traité
                        chunk_hash = self._generate_hash(chunk)
                        if chunk_hash in self._processed_chunks:
                            continue

                        # Générer l'embedding et stocker
                        embedding = await self.embedding.get_embedding(chunk)
                        await self.vector_store.add_vectors(
                            vectors=[embedding],
                            payloads=[{
                                **metadata,
                                "page_number": page_num + 1,
                                "chunk_index": chunks_processed,
                                "text": chunk,
                                "chunk_hash": chunk_hash,
                                "indexed_at": datetime.utcnow().isoformat()
                            }]
                        )
                        
                        self._processed_chunks.add(chunk_hash)
                        chunks_processed += 1
                        
                        await asyncio.sleep(self.rate_limit_delay)
                        
                except Exception as e:
                    logger.error(f"Error processing page {page_num + 1}: {str(e)}")
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
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "file": file_path,
                "error": str(e),
                "chunks_processed": 0
            }
        finally:
            if doc:
                doc.close()

    def _split_text(self, text: str) -> List[str]:
        """
        Découpe un texte en chunks avec chevauchement.
        """
        chunks = []
        current_pos = 0
        text = text.strip()
        
        if not text:  # Ignorer les textes vides
            return chunks

        while current_pos < len(text):
            # Trouver une bonne fin de chunk
            end_pos = min(current_pos + self.chunk_size, len(text))
            
            if end_pos < len(text):
                # Chercher la dernière phrase complète
                last_period = text.rfind(".", current_pos, end_pos)
                if last_period != -1:
                    end_pos = last_period + 1

            chunk = text[current_pos:end_pos].strip()
            if chunk:  # Ignorer les chunks vides
                chunks.append(chunk)
            
            # Avancer avec chevauchement
            current_pos = max(current_pos + 1, end_pos - self.chunk_overlap)

        return chunks

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