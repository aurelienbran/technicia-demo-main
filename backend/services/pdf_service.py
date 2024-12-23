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
        self.model = "voyage-multimodal-3"
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
        
    async def process_pdf(self, file: bytes, filename: str) -> Dict:
        """Process and index a PDF file"""
        print(f"Traitement du fichier {filename}")
        
        # Sauvegarder le PDF
        file_path = self.storage_path / filename
        file_path.write_bytes(file)
        
        # Extraire le texte et les images
        doc = fitz.open(str(file_path))
        chunks_with_embeddings = []
        
        for page_num, page in enumerate(doc, 1):
            print(f"Traitement de la page {page_num}")
            
            # Extraire le texte
            text_content = page.get_text()
            
            # Extraire les images
            image_list = page.get_images()
            page_images = []
            
            for img_idx, img_info in enumerate(image_list):
                try:
                    base_image = doc.extract_image(img_info[0])
                    # Vérifier si l'image est significative (taille minimale)
                    if base_image and base_image["width"] > 100 and base_image["height"] > 100:
                        # Générer un ID unique pour cette image
                        image_id = str(uuid.uuid4())
                        
                        # Générer embedding multimodal
                        image_embedding = self.voyage_client.embed(
                            [base_image["image"]],
                            model=self.model,
                            input_type="image"
                        ).embeddings[0]
                        
                        # Préparer les métadonnées
                        metadata = {
                            'filename': filename,
                            'page_num': page_num,
                            'type': 'image',
                            'width': base_image["width"],
                            'height': base_image["height"]
                        }
                        
                        chunks_with_embeddings.append({
                            'id': image_id,
                            'embedding': image_embedding,
                            'metadata': metadata
                        })
                        
                except Exception as e:
                    print(f"Erreur lors du traitement de l'image {img_idx}: {str(e)}")
            
            # Diviser le texte en morceaux si nécessaire (limite de tokens)
            chunk_size = 1000  # Ajuster selon les limites du modèle
            text_chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size)]
            
            # Générer embeddings pour chaque morceau de texte
            for chunk in text_chunks:
                if chunk.strip():  # Vérifier que le chunk n'est pas vide
                    # Générer un ID unique pour ce chunk
                    chunk_id = str(uuid.uuid4())
                    
                    # Créer l'embedding
                    embedding = self.voyage_client.embed(
                        [chunk],
                        model=self.model,
                        input_type="document"
                    ).embeddings[0]
                    
                    # Préparer les métadonnées
                    metadata = {
                        'filename': filename,
                        'page_num': page_num,
                        'chunk_text': chunk,
                        'type': 'text'
                    }
                    
                    # Ajouter à notre liste
                    chunks_with_embeddings.append({
                        'id': chunk_id,
                        'embedding': embedding,
                        'metadata': metadata
                    })
            
            print(f"Page {page_num}: {len(text_chunks)} chunks de texte et {len(page_images)} images indexés")
            
        doc.close()
        
        # Ajouter tous les vecteurs à Qdrant
        vectors = [item['embedding'] for item in chunks_with_embeddings]
        metadata = [item['metadata'] for item in chunks_with_embeddings]
        ids = [item['id'] for item in chunks_with_embeddings]
        
        self.vector_store.add_vectors(vectors, metadata, ids)
        
        # Créer l'entrée d'index
        index_entry = {
            'filename': filename,
            'path': str(file_path),
            'upload_date': datetime.now().isoformat(),
            'page_count': doc.page_count,
            'chunk_ids': ids
        }
        
        # Mettre à jour l'index
        self.index[filename] = index_entry
        self.save_index()
        
        return index_entry
    
    async def process_directory(self, directory_path: str) -> List[Dict]:
        """Process tous les PDFs d'un dossier"""
        path = Path(directory_path)
        results = []
        
        for pdf_file in path.glob('**/*.pdf'):
            try:
                file_content = pdf_file.read_bytes()
                result = await self.process_pdf(file_content, pdf_file.name)
                results.append({
                    'filename': pdf_file.name,
                    'status': 'success',
                    'details': result
                })
            except Exception as e:
                results.append({
                    'filename': pdf_file.name,
                    'status': 'error',
                    'error': str(e)
                })
                
        return results
    
    def get_index_info(self) -> Dict:
        """Retourne des informations sur l'index"""
        collection_info = self.vector_store.get_collection_info()
        return {
            'total_files': len(self.index),
            'indexed_vectors': collection_info['vectors_count'],
            'storage_size': sum(f.stat().st_size for f in self.storage_path.glob('*.pdf')) // 1024  # KB
        }
    
    def search_content(self, query: str, limit: int = 5) -> List[Dict]:
        """Recherche dans le contenu des PDFs indexés"""
        # Générer l'embedding de la requête
        query_embedding = self.voyage_client.embed(
            [query],
            model=self.model,
            input_type="query"
        ).embeddings[0]
        
        # Rechercher dans Qdrant
        results = self.vector_store.search(query_embedding, limit=limit)
        
        # Formater les résultats
        formatted_results = []
        for result in results:
            metadata = result['metadata']
            if metadata['type'] == 'text':
                formatted_results.append({
                    'filename': metadata['filename'],
                    'page_num': metadata['page_num'],
                    'text': metadata['chunk_text'],
                    'type': 'text',
                    'score': result['score']
                })
            else:  # type == 'image'
                formatted_results.append({
                    'filename': metadata['filename'],
                    'page_num': metadata['page_num'],
                    'type': 'image',
                    'dimensions': f"{metadata['width']}x{metadata['height']}",
                    'score': result['score']
                })
            
        return formatted_results
    
    def get_indexed_files(self) -> List[str]:
        """Liste tous les fichiers indexés"""
        return list(self.index.keys())
    
    def clear_storage(self):
        """Nettoie le stockage et l'index"""
        # Vider Qdrant
        self.vector_store.clear_collection()
        
        # Supprimer les fichiers PDF stockés
        if self.storage_path.exists():
            shutil.rmtree(self.storage_path)
            self.storage_path.mkdir(parents=True)
            
        # Réinitialiser l'index
        self.index = {}
        self.save_index()