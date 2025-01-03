import logging
import hashlib
import os
from typing import List, Dict, Optional
import fitz  # PyMuPDF

logger = logging.getLogger("technicia.indexing")

class IndexingService:
    def __init__(self, embedding_service, vector_store):
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.chunk_size = 1500
        self.chunk_overlap = 300

    def _get_file_hash(self, file_path: str) -> str:
        """Generate a unique hash for a file based on its path, size, and modification time."""
        try:
            file_stat = os.stat(file_path)
            file_info = f"{file_path}|{file_stat.st_size}|{file_stat.st_mtime}"
            return hashlib.sha256(file_info.encode()).hexdigest()
        except Exception as e:
            logger.error(f"Error generating file hash: {e}")
            raise

    def _extract_text_from_pdf(self, file_path: str) -> List[Dict[str, any]]:
        """Extract text from PDF and split into chunks."""
        try:
            doc = fitz.open(file_path)
            text_chunks = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                
                if not text.strip():
                    continue
                
                # Split text into chunks
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

    async def process_file(self, file_path: str) -> bool:
        """Process a PDF file for indexing."""
        try:
            file_hash = self._get_file_hash(file_path)
            
            # Check if file already exists in vector store
            if self.vector_store.file_exists(file_path):
                logger.info(f"File {file_path} already indexed, skipping")
                return True
            
            # Extract text chunks from PDF
            chunks = self._extract_text_from_pdf(file_path)
            if not chunks:
                logger.warning(f"No text extracted from {file_path}")
                return False
            
            # Prepare data for embedding
            texts = [chunk["text"] for chunk in chunks]
            metadatas = [
                {
                    "file_path": file_path,
                    "page": chunk["page"],
                    "chunk_index": chunk["chunk_index"],
                    "chunk_id": f"{file_hash}_{chunk['chunk_index']}"
                }
                for chunk in chunks
            ]
            
            # Generate embeddings
            embeddings = await self.embedding_service.get_embeddings(texts)
            if not embeddings:
                logger.error("Failed to generate embeddings")
                return False
            
            # Add to vector store
            success = await self.vector_store.add_texts(texts, metadatas, embeddings)
            if success:
                logger.info(f"Successfully indexed {file_path}")
                return True
            else:
                logger.error(f"Failed to add vectors to store for {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False