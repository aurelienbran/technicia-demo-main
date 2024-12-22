from typing import List, Dict
from pathlib import Path, WindowsPath
import fitz  # PyMuPDF
from datetime import datetime
import os
import shutil

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
        doc = fitz.open(str(file_path))
        text_content = []
        for page in doc:
            text_content.append(page.get_text())
        doc.close()
        
        # Créer l'index
        index_entry = {
            'filename': filename,
            'path': str(file_path),
            'upload_date': datetime.now().isoformat(),
            'page_count': len(text_content),
            'content': text_content
        }
        
        return index_entry
    
    async def process_directory(self, directory_path: str) -> List[Dict]:
        """Process all PDFs in a directory"""
        results = []
        # Convertit le chemin Windows en objet Path
        source_dir = WindowsPath(directory_path)
        
        # Vérifie si le dossier existe
        if not source_dir.exists() or not source_dir.is_dir():
            raise ValueError(f"Le dossier {str(source_dir)} n'existe pas ou n'est pas un dossier")
            
        # Parcourt tous les fichiers PDF du dossier
        for file_path in source_dir.glob('**/*.pdf'):
            try:
                print(f"Traitement du fichier : {file_path}")
                # Lit le fichier
                content = file_path.read_bytes()
                
                # Traite le PDF
                result = await self.process_pdf(content, file_path.name)
                results.append(result)
                
            except Exception as e:
                error_details = {
                    'filename': file_path.name,
                    'path': str(file_path),
                    'error': str(e)
                }
                print(f"Erreur lors du traitement : {error_details}")
                results.append(error_details)
                
        return results
    
    def get_indexed_files(self) -> List[str]:
        """Retourne la liste des fichiers indexés"""
        return [f.name for f in self.storage_path.glob('*.pdf')]
        
    def clear_storage(self):
        """Nettoie le dossier de stockage"""
        if self.storage_path.exists():
            shutil.rmtree(str(self.storage_path))
        self.storage_path.mkdir(parents=True, exist_ok=True)