import logging
import asyncio
from typing import List, Dict
from datetime import datetime
from pathlib import Path
import hashlib
import fitz
import numpy as np

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
        self._processed_hashes = set()

    async def index_document(self, file_path: str) -> Dict:
        try:
            # Lire le PDF
            doc = fitz.open(file_path)
            metadata = {
                "filename": Path(file_path).name,
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "doc_type": "pdf",
                "page_count": len(doc),
                "file_path": file_path,
            }

            # Extraire le texte
            chunks = []
            for page_num in range(len(doc)):
                text = doc[page_num].get_text()
                if text.strip():
                    chunks.extend(self._split_text(text, page_num + 1))
            doc.close()

            # Indexer les chunks
            for i, (chunk, page_num) in enumerate(chunks):
                chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
                if chunk_hash in self._processed_hashes:
                    continue

                embedding = await self.embedding.get_embedding(chunk)
                payload = {
                    **metadata,
                    "page_number": page_num,
                    "chunk_index": i,
                    "text": chunk,
                    "chunk_hash": chunk_hash,
                    "indexed_at": datetime.utcnow().isoformat()
                }

                await self.vector_store.add_vectors(
                    vectors=[embedding],
                    payloads=[payload]
                )
                self._processed_hashes.add(chunk_hash)

            return {
                "status": "success",
                "file": file_path,
                "chunks_processed": len(chunks)
            }

        except Exception as e:
            logger.error(f"Error indexing document: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    def _split_text(self, text: str, page_num: int) -> List[tuple[str, int]]:
        """Découpe le texte en chunks avec chevauchement."""
        chunks = []
        words = text.split()
        current_chunk = []
        current_length = 0

        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1

            if current_length >= settings.CHUNK_SIZE:
                chunk_text = " ".join(current_chunk)
                chunks.append((chunk_text, page_num))
                overlap_start = max(0, len(current_chunk) - settings.CHUNK_OVERLAP)
                current_chunk = current_chunk[overlap_start:]
                current_length = sum(len(w) + 1 for w in current_chunk)

        if current_chunk:  # Ajouter le dernier chunk
            chunks.append((" ".join(current_chunk), page_num))

        return chunks

    async def search(self, query: str, limit: int = 5) -> Dict:
        try:
            query_embedding = await self.embedding.get_embedding(query)
            results = await self.vector_store.search(
                query_vector=query_embedding,
                limit=limit
            )

            if not results:
                return {
                    "answer": "Aucun résultat pertinent trouvé.",
                    "sources": []
                }

            context = "\n---\n".join(
                result["payload"]["text"]
                for result in results
                if "text" in result["payload"]
            )

            prompt = (
                f"En te basant sur ce contenu technique, réponds à cette question: {query}\n\n"
                f"Contenu de référence:\n{context}"
            )

            answer = await self.claude.get_response(prompt)
            return {"answer": answer, "sources": results}

        except Exception as e:
            logger.error(f"Error searching: {str(e)}")
            return {
                "answer": "Une erreur s'est produite lors de la recherche.",
                "sources": []
            }