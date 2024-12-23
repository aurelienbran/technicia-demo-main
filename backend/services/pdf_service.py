from typing import List, Dict
from pathlib import Path, WindowsPath
import fitz  # PyMuPDF
from datetime import datetime
import os
import shutil
import json
from dotenv import load_dotenv
import voyageai
from .vector_store import VectorStore
import uuid

# Charger les variables d'environnement
load_dotenv()

class PDFService:
    def __init__(self, storage_path: str = 'storage/pdfs', index_path: str = 'storage/index'):
        self.storage_path = Path(storage_path)
        self.index_path = Path(index_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.index_path / 'content_index.json'
        
        # Initialiser les clients
        self.voyage_client = voyageai.Client()
        self.vector_store = VectorStore()
        self.model = "voyage-2"  # Changé pour utiliser voyage-2 au lieu de multimodal
        print(f"Initialisé avec le modèle {self.model}")
        
        self.load_index()
        
    def load_index(self):
        """Charge l'index existant ou en crée un nouveau"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
                print(f"Index chargé avec {len(self.index)} documents")
        else:
            self.index = {}
            print("Nouvel index créé")
            
    def save_index(self):
        """Sauvegarde l'index sur le disque"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
        print(f"Index sauvegardé avec {len(self.index)} documents")

    def _extract_text_from_pdf(self, doc) -> List[Dict]:
        """Extrait et vectorise le texte d'un document PDF"""
        chunks_with_embeddings = []
        for page_num, page in enumerate(doc, 1):
            text_content = page.get_text().strip()
            if not text_content:  # Skip empty pages
                continue
                
            # Diviser le texte en morceaux
            chunk_size = 1000
            text_chunks = [text_content[i:i+chunk_size] 
                         for i in range(0, len(text_content), chunk_size)]
            
            for chunk in text_chunks:
                if chunk.strip():  # Vérifier que le chunk n'est pas vide
                    try:
                        # Générer l'embedding
                        embedding = self.voyage_client.embed(
                            [chunk],
                            model=self.model,
                            input_type="document"
                        ).embeddings[0]
                        
                        chunks_with_embeddings.append({
                            'id': str(uuid.uuid4()),
                            'text': chunk,
                            'page_num': page_num,
                            'embedding': embedding
                        })
                    except Exception as e:
                        print(f"Erreur lors de la vectorisation: {str(e)}")
                        
        return chunks_with_embeddings
        
    async def process_pdf(self, file: bytes, filename: str) -> Dict:
        """Process and index a PDF file"""
        print(f"Traitement du fichier {filename}")
        
        # Vérifier que c'est bien un PDF
        if not filename.lower().endswith('.pdf'):
            raise ValueError("Le fichier doit être un PDF")
            
        # Sauvegarder le PDF
        file_path = self.storage_path / filename
        file_path.write_bytes(file)
        
        try:
            # Extraire le texte
            doc = fitz.open(str(file_path))
            chunks = self._extract_text_from_pdf(doc)
            doc.close()
            
            if not chunks:
                raise ValueError("Aucun contenu textuel exploitable trouvé dans le PDF")
            
            # Préparer les données pour Qdrant
            vectors = [chunk['embedding'] for chunk in chunks]
            metadata = [
                {
                    'filename': filename,
                    'page_num': chunk['page_num'],
                    'chunk_text': chunk['text']
                } 
                for chunk in chunks
            ]
            ids = [chunk['id'] for chunk in chunks]
            
            # Ajouter à Qdrant
            self.vector_store.add_vectors(vectors, metadata, ids)
            
            # Créer l'entrée d'index
            index_entry = {
                'filename': filename,
                'path': str(file_path),
                'upload_date': datetime.now().isoformat(),
                'page_count': doc.page_count if doc else 0,
                'chunk_count': len(chunks),
                'chunk_ids': ids
            }
            
            # Mettre à jour l'index
            self.index[filename] = index_entry
            self.save_index()
            
            return index_entry
            
        except Exception as e:
            # Nettoyer en cas d'erreur
            if file_path.exists():
                file_path.unlink()
            raise e