from typing import List, Dict
from pathlib import Path, WindowsPath
import fitz  # PyMuPDF
from datetime import datetime
import os
import shutil
import json
from dotenv import load_dotenv
from voyage_embeddings.client import VoyageClient

# Charger les variables d'environnement
load_dotenv()

class PDFService:
    def __init__(self, storage_path: str = 'storage/pdfs', index_path: str = 'storage/index'):
        self.storage_path = Path(storage_path)
        self.index_path = Path(index_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.index_path / 'content_index.json'
        
        # Initialiser le client Voyage AI
        self.voyage_client = VoyageClient(
            api_key=os.getenv('VOYAGE_API_KEY'),
            model=os.getenv('VOYAGE_MODEL', 'voyage-2-multimodal')
        )
        
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
        pages_content = []
        
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
                        # Générer embedding multimodal
                        image_embedding = self.voyage_client.embed_image(base_image["image"])
                        page_images.append({
                            'image_idx': img_idx,
                            'embedding': image_embedding
                        })
                except Exception as e:
                    print(f"Erreur lors du traitement de l'image {img_idx}: {str(e)}")
            
            # Générer embedding pour le texte
            text_embedding = self.voyage_client.embed_text(text_content)
            
            pages_content.append({
                'page_num': page_num,
                'text': text_content,
                'text_embedding': text_embedding,
                'images': page_images
            })
            
            print(f"Page {page_num}: {len(text_content)} caractères, {len(page_images)} images indexées")
            
        doc.close()
        
        # Créer l'entrée d'index
        index_entry = {
            'filename': filename,
            'path': str(file_path),
            'upload_date': datetime.now().isoformat(),
            'page_count': len(pages_content),
            'content': pages_content
        }
        
        # Mettre à jour l'index
        self.index[filename] = index_entry
        self.save_index()
        
        return index_entry
    
    def search_content(self, query: str) -> List[Dict]:
        """Recherche dans le contenu indexé en utilisant la similarité sémantique"""
        print(f"Recherche de '{query}' dans {len(self.index)} documents")
        
        # Générer l'embedding de la requête
        query_embedding = self.voyage_client.embed_text(query)
        
        results = []
        for filename, doc_info in self.index.items():
            doc_matches = []
            
            for page in doc_info['content']:
                # Calculer la similarité avec le texte de la page
                text_similarity = self.voyage_client.similarity(
                    query_embedding,
                    page['text_embedding']
                )
                
                # Si la page contient des images, calculer aussi leur similarité
                image_similarities = []
                for img in page['images']:
                    img_similarity = self.voyage_client.similarity(
                        query_embedding,
                        img['embedding']
                    )
                    if img_similarity > 0.7:  # Seuil de similarité pour les images
                        image_similarities.append(img_similarity)
                
                if text_similarity > 0.7 or image_similarities:  # Seuil de similarité
                    doc_matches.append({
                        'page': page['page_num'],
                        'text_similarity': text_similarity,
                        'image_matches': len(image_similarities),
                        'max_image_similarity': max(image_similarities) if image_similarities else 0,
                        'context': page['text'][:200]  # Contexte limité
                    })
            
            if doc_matches:
                # Trier les résultats par similarité décroissante
                doc_matches.sort(key=lambda x: max(x['text_similarity'], x['max_image_similarity']), reverse=True)
                results.append({
                    'filename': filename,
                    'matches': doc_matches[:5]  # Limiter à 5 meilleurs résultats par document
                })
        
        # Trier les documents par meilleure similarité
        results.sort(
            key=lambda x: max(m['text_similarity'] for m in x['matches']),
            reverse=True
        )
        
        return results