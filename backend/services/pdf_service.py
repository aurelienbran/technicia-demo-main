from typing import List, Dict
from pathlib import Path, WindowsPath
import fitz  # PyMuPDF
from datetime import datetime
import os
import shutil
import json

class PDFService:
    def __init__(self, storage_path: str = 'storage/pdfs', index_path: str = 'storage/index'):
        self.storage_path = Path(storage_path)
        self.index_path = Path(index_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.index_path / 'content_index.json'
        self.load_index()
        
    def load_index(self):
        """Charge l'index existant ou en crée un nouveau"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
        else:
            self.index = {}
            
    def save_index(self):
        """Sauvegarde l'index sur le disque"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
        
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
        
        # Créer l'entrée d'index
        index_entry = {
            'filename': filename,
            'path': str(file_path),
            'upload_date': datetime.now().isoformat(),
            'page_count': len(text_content),
            'content': text_content
        }
        
        # Mettre à jour l'index
        self.index[filename] = index_entry
        self.save_index()
        
        return index_entry
    
    async def process_directory(self, directory_path: str) -> List[Dict]:
        """Process all PDFs in a directory"""
        results = []
        source_dir = WindowsPath(directory_path)
        
        if not source_dir.exists() or not source_dir.is_dir():
            raise ValueError(f"Le dossier {str(source_dir)} n'existe pas ou n'est pas un dossier")
            
        for file_path in source_dir.glob('**/*.pdf'):
            try:
                print(f"Traitement du fichier : {file_path}")
                content = file_path.read_bytes()
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
    
    def search_content(self, query: str, context_size: int = 100) -> List[Dict]:
        """Recherche un terme dans tous les PDFs indexés"""
        results = []
        query = query.lower()
        
        for filename, doc_info in self.index.items():
            matches = []
            total_occurrences = 0
            
            # Parcourir chaque page
            for page_num, page_content in enumerate(doc_info['content']):
                page_text = page_content.lower()
                start = 0
                
                # Trouver toutes les occurrences dans la page
                while True:
                    pos = page_text.find(query, start)
                    if pos == -1:
                        break
                        
                    total_occurrences += 1
                    
                    # Extraire le contexte autour du terme trouvé
                    context_start = max(0, pos - context_size)
                    context_end = min(len(page_text), pos + len(query) + context_size)
                    context = page_text[context_start:context_end]
                    
                    matches.append({
                        'page': page_num + 1,
                        'context': context.strip(),
                        'position': pos
                    })
                    
                    start = pos + len(query)
                    
                    # Limiter le nombre de résultats par document
                    if len(matches) >= 5:
                        break
                        
            if matches:
                results.append({
                    'filename': filename,
                    'total_occurrences': total_occurrences,
                    'matches': matches[:5]  # Limiter à 5 extraits par document
                })
        
        # Trier les résultats par nombre d'occurrences
        results.sort(key=lambda x: x['total_occurrences'], reverse=True)
        return results
    
    def get_indexed_files(self) -> List[str]:
        """Retourne la liste des fichiers indexés"""
        return list(self.index.keys())
        
    def clear_storage(self):
        """Nettoie le stockage des PDFs et l'index"""
        if self.storage_path.exists():
            shutil.rmtree(str(self.storage_path))
        if self.index_path.exists():
            shutil.rmtree(str(self.index_path))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.index = {}
