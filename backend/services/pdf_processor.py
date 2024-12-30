import fitz
from typing import List, Dict
from .voyage_embedding import VoyageEmbedding

class PDFProcessor:
    def __init__(self):
        self.embedder = VoyageEmbedding()
        self.chunk_size = 1000
    
    def extract_text(self, pdf_path: str) -> List[str]:
        doc = fitz.open(pdf_path)
        chunks = []
        buffer = ""
        
        for page in doc:
            text = page.get_text()
            buffer += text
            
            while len(buffer) >= self.chunk_size:
                chunks.append(buffer[:self.chunk_size])
                buffer = buffer[self.chunk_size:]
        
        if buffer:
            chunks.append(buffer)
            
        return chunks
    
    async def process_pdf(self, pdf_path: str) -> List[Dict]:
        chunks = self.extract_text(pdf_path)
        embeddings = await self.embedder.get_embeddings(chunks)
        
        return [{
            "text": chunk,
            "embedding": embedding
        } for chunk, embedding in zip(chunks, embeddings)]