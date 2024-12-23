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
        
        # Initialiser le client Voyage AI avec voyage-multimodal-3
        self.voyage_client = VoyageClient(
            api_key=os.getenv('VOYAGE_API_KEY'),
            model=os.getenv('VOYAGE_MODEL', 'voyage-multimodal-3')
        )
        print(f"Initialisé avec le modèle {os.getenv('VOYAGE_MODEL', 'voyage-multimodal-3')}")
        
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
            
            # Diviser le texte en morceaux si nécessaire (limite de tokens)
            chunk_size = 1000  # Ajuster selon les limites du modèle
            text_chunks = [text_content[i:i+chunk_size] for i in range(0, len(text_content), chunk_size)]
            
            # Générer embedding pour chaque morceau de texte
            text_embeddings = []
            for chunk in text_chunks:
                if chunk.strip():  # Vérifier que le chunk n'est pas vide
                    embedding = self.voyage_client.embed_text(chunk)
                    text_embeddings.append({
                        'text': chunk,
                        'embedding': embedding
                    })
            
            pages_content.append({
                'page_num': page_num,
                'text_chunks': text_embeddings,
                'images': page_images
            })
            
            print(f"Page {page_num}: {len(text_chunks)} chunks de texte, {len(page_images)} images indexées")
            
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
                page_matches = []
                
                # Vérifier la similarité avec chaque chunk de texte
                for chunk in page['text_chunks']:
                    similarity = self.voyage_client.similarity(
                        query_embedding,
                        chunk['embedding']
                    )
                    if similarity > 0.7:  # Seuil de similarité
                        page_matches.append({
                            'text': chunk['text'],
                            'similarity': similarity
                        })
                
                # Vérifier la similarité avec les images
                image_matches = []
                for img in page['images']:
                    similarity = self.voyage_client.similarity(
                        query_embedding,
                        img['embedding']
                    )
                    if similarity > 0.7:
                        image_matches.append(similarity)
                
                if page_matches or image_matches:
                    doc_matches.append({
                        'page': page['page_num'],
                        'text_matches': sorted(page_matches, key=lambda x: x['similarity'], reverse=True)[:3],
                        'image_matches': len(image_matches),
                        'max_image_similarity': max(image_matches) if image_matches else 0
                    })
            
            if doc_matches:
                # Trier les résultats par similarité décroissante
                doc_matches.sort(
                    key=lambda x: max(
                        [m['similarity'] for m in x['text_matches']] + [x['max_image_similarity']]
                    ),
                    reverse=True
                )
                results.append({
                    'filename': filename,
                    'matches': doc_matches[:5]  # Limiter à 5 meilleurs résultats par document
                })
        
        # Trier les documents par meilleure similarité
        results.sort(
            key=lambda x: max(
                max(m['similarity'] for match in x['matches'] for m in match['text_matches'])
                if x['matches'] and x['matches'][0]['text_matches']
                else 0,
                max(match['max_image_similarity'] for match in x['matches'])
            ),
            reverse=True
        )
        
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
        print("Stockage et index nettoyés")