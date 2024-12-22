from typing import List, Dict
from pathlib import Path
import fitz  # PyMuPDF
from datetime import datetime

class PDFService:
    def __init__(self, storage_path: str = 'storage/pdfs'):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    async def process_pdf(self, file: bytes, filename: str) -> Dict:
        """Process and index a PDF file"""
        # Sauvegarder le PDF
        file_path = self.storage_path / filename
        file_path.write_bytes(file)
        
        # Extraire le texte
        doc = fitz.open(file_path)
        text_content = []
        for page in doc:
            text_content.append(page.get_text())
        
        # Créer l'index
        index_entry = {
            'filename': filename,
            'path': str(file_path),
            'upload_date': datetime.now().isoformat(),
            'page_count': len(text_content),
            'content': text_content
        }
        
        return index_entry
    
    def get_indexed_files(self) -> List[str]:
        """Retourne la liste des fichiers indexés"""
        return [f.name for f in self.storage_path.glob('*.pdf')]