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
            
            total_chunks = 0
            chunks_dict = {}
            
            # Première passe : collecter tous les chunks
            for page_num in range(len(doc)):
                logger.info(f"Processing page {page_num + 1} of {len(doc)}")
                page = doc[page_num]
                page_text = page.get_text().strip()
                
                if not page_text:  # Ignorer les pages vides
                    continue
                    
                # Découper la page en chunks
                page_chunks = []
                current_chunk = ""
                sentences = page_text.replace('\n', ' ').split('.')
                
                for sentence in sentences:
                    sentence = sentence.strip() + "."
                    if len(current_chunk) + len(sentence) > self.chunk_size:
                        if current_chunk:
                            page_chunks.append(current_chunk)
                        current_chunk = sentence
                    else:
                        current_chunk += " " + sentence if current_chunk else sentence
                
                if current_chunk:  # Ne pas oublier le dernier chunk
                    page_chunks.append(current_chunk)
                
                chunks_dict[page_num] = page_chunks
                total_chunks += len(page_chunks)
            
            # Deuxième passe : indexer les chunks
            chunks_processed = 0
            for page_num, page_chunks in chunks_dict.items():
                for chunk in page_chunks:
                    chunk = chunk.strip()
                    if not chunk:
                        continue
                    
                    chunk_hash = self._generate_hash(chunk)
                    if chunk_hash in self._processed_chunks:
                        logger.debug(f"Skipping duplicate chunk: {chunk[:50]}...")
                        continue
                    
                    # Générer l'embedding
                    try:
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
                        logger.info(f"Processed chunk {chunks_processed}/{total_chunks} (page {page_num + 1})")
                        
                        # Rate limiting
                        await asyncio.sleep(self.rate_limit_delay)
                        
                    except Exception as e:
                        logger.error(f"Error processing chunk on page {page_num + 1}: {str(e)}")
                        continue

            logger.info(f"Successfully indexed {file_path}: {chunks_processed} chunks processed")
            return {
                "status": "success",
                "file": file_path,
                "chunks_processed": chunks_processed,
                "total_chunks": total_chunks,
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