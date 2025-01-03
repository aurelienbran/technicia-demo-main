import logging
import hashlib
import os
from typing import List, Dict, Optional
from .claude import ClaudeService
from .embedding import EmbeddingService
from .vector_store import VectorStore
import fitz

logger = logging.getLogger("technicia.indexing")

class IndexingService:
    def __init__(self):
        self.claude = ClaudeService()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()
        self.chunk_size = 1500
        self.chunk_overlap = 300
        self._hashes = {}

    def _get_file_hash(self, file_path: str) -> str:
        try:
            file_stat = os.stat(file_path)
            file_info = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
            return hashlib.sha256(file_info.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error generating file hash: {e}")
            raise

    def _extract_text_from_pdf(self, file_path: str) -> List[Dict[str, any]]:
        try:
            doc = fitz.open(file_path)
            text_chunks = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                if not text.strip():
                    continue
                
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
            
            return text_chunks
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise

    async def index_document(self, file_path: str) -> Dict:
        try:
            current_hash = self._get_file_hash(file_path)
            
            if file_path in self._hashes and self._hashes[file_path] == current_hash:
                logger.info(f"File {file_path} already indexed")
                return {"status": "success", "file": file_path, "message": "File already indexed"}

            chunks = self._extract_text_from_pdf(file_path)
            if not chunks:
                return {"status": "error", "file": file_path, "error": "No text extracted"}

            texts = [chunk["text"] for chunk in chunks]
            embeddings = await self.embedding_service.get_embeddings(texts)

            if not embeddings:
                return {"status": "error", "file": file_path, "error": "Failed to generate embeddings"}

            await self.vector_store.clear_file(file_path)  # Remove old vectors if they exist
            
            metadatas = [
                {
                    "file_path": file_path,
                    "page": chunk["page"],
                    "chunk_index": chunk["chunk_index"],
                    "hash": current_hash
                }
                for chunk in chunks
            ]

            success = await self.vector_store.add_texts(texts, metadatas, embeddings)
            if not success:
                return {"status": "error", "file": file_path, "error": "Failed to add to vector store"}

            self._hashes[file_path] = current_hash
            return {
                "status": "success",
                "file": file_path,
                "chunks_processed": len(chunks),
                "metadata": {"pages": len(set(chunk["page"] for chunk in chunks))}
            }

        except Exception as e:
            logger.error(f"Error indexing document: {e}")
            return {"status": "error", "file": file_path, "error": str(e)}

    async def search(self, query: str, limit: int = 5) -> Dict:
        try:
            query_embedding = await self.embedding_service.get_embeddings([query])
            if not query_embedding:
                raise Exception("Failed to generate query embedding")

            similar_texts = await self.vector_store.similarity_search(query_embedding[0], k=limit)
            if not similar_texts:
                return {
                    "answer": "Je suis désolé, je n'ai pas trouvé d'information pertinente dans la documentation disponible.",
                    "sources": []
                }

            context = "\n\n---\n\n".join([text[0]["text"] for text in similar_texts])
            
            prompt = f"Question: {query}\n\nContexte: {context}\n\nRépondez à la question en vous basant uniquement sur le contexte fourni. Si vous ne trouvez pas l'information dans le contexte, dites-le clairement."
            
            answer = await self.claude.generate_response(prompt)

            return {
                "answer": answer,
                "sources": [{
                    "id": idx,
                    "score": text[1],
                    "payload": text[0]
                } for idx, text in enumerate(similar_texts)]
            }

        except Exception as e:
            logger.error(f"Error in search: {e}")
            raise