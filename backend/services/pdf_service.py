from typing import List, Dict
from pathlib import Path, WindowsPath
import fitz  # PyMuPDF
from datetime import datetime
import os
import shutil
import json
from dotenv import load_dotenv
import voyageai
import base64
import io
from PIL import Image
from .vector_store import VectorStore
import uuid
import aiohttp

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
        self.voyage_api_key = os.getenv('VOYAGE_API_KEY')
        self.vector_store = VectorStore()
        self.model = "voyage-multimodal-3"
        print(f"Initialisé avec le modèle {self.model}")
        
        self.index = {}
        self.load_index()

    def load_index(self):
        """Charge l'index existant ou en crée un nouveau"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.index = json.load(f)
                print(f"Index chargé avec {len(self.index)} documents")
        else:
            print("Nouvel index créé")

    def save_index(self):
        """Sauvegarde l'index sur le disque"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
        print(f"Index sauvegardé avec {len(self.index)} documents")

    def _image_to_base64(self, image) -> str:
        """Convertit une image en base64 pour l'API Voyage"""
        buffered = io.BytesIO()
        if not isinstance(image, Image.Image):
            image = Image.open(io.BytesIO(image))
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"
        
    def _create_multimodal_content(self, text: str, images: List[bytes] = None) -> List[Dict]:
        """Crée le contenu multimodal pour l'API Voyage"""
        content = []
        
        # Ajouter le texte
        if text.strip():
            content.append({
                "type": "text",
                "text": text.strip()
            })
        
        # Ajouter les images
        if images:
            for img in images:
                content.append({
                    "type": "image_base64",
                    "image_base64": self._image_to_base64(img)
                })
        
        return content

    async def get_multimodal_embedding(self, text: str, images: List[bytes] = None) -> List[float]:
        """Obtient l'embedding pour du contenu multimodal"""
        content = self._create_multimodal_content(text, images)
        if not content:
            raise ValueError("Aucun contenu valide fourni pour l'embedding")
        
        headers = {
            "Authorization": f"Bearer {self.voyage_api_key}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.voyageai.com/v1/multimodalembeddings",
                json={
                    "inputs": [{"content": content}],
                    "model": self.model,
                    "input_type": "document"
                },
                headers=headers
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result['data'][0]['embedding']
                else:
                    error_text = await response.text()
                    raise ValueError(f"Erreur API Voyage: {error_text}")

    def _extract_images_from_page(self, page) -> List[bytes]:
        """Extrait les images d'une page PDF"""
        images = []
        for img in page.get_images(full=True):
            try:
                xref = img[0]
                base_image = page.parent.extract_image(xref)
                if base_image and base_image['width'] > 100 and base_image['height'] > 100:
                    images.append(base_image['image'])
            except Exception as e:
                print(f"Erreur lors de l'extraction d'image: {str(e)}")
        return images

    async def process_pdf(self, file: bytes, filename: str) -> Dict:
        """Process and index a PDF file"""
        print(f"Traitement du fichier {filename}")
        
        # Vérifier que c'est bien un PDF
        if not filename.lower().endswith('.pdf'):
            raise ValueError("Le fichier doit être un PDF")
            
        # Sauvegarder le PDF
        file_path = self.storage_path / filename
        file_path.write_bytes(file)
        
        doc = None
        try:
            # Extraire le texte et les images
            doc = fitz.open(str(file_path))
            chunks = []
            
            for page_num, page in enumerate(doc, 1):
                text_content = page.get_text().strip()
                images = self._extract_images_from_page(page)
                
                if text_content or images:
                    # Générer l'embedding multimodal
                    try:
                        embedding = await self.get_multimodal_embedding(text_content, images)
                        
                        chunks.append({
                            'id': str(uuid.uuid4()),
                            'text': text_content,
                            'has_images': bool(images),
                            'image_count': len(images),
                            'page_num': page_num,
                            'embedding': embedding
                        })
                    except Exception as e:
                        print(f"Erreur lors de la vectorisation de la page {page_num}: {str(e)}")
            
            if not chunks:
                raise ValueError("Aucun contenu exploitable trouvé dans le PDF")
            
            # Ajouter à Qdrant
            vectors = [chunk['embedding'] for chunk in chunks]
            metadata = [{
                'filename': filename,
                'page_num': chunk['page_num'],
                'text': chunk['text'],
                'has_images': chunk['has_images'],
                'image_count': chunk['image_count']
            } for chunk in chunks]
            ids = [chunk['id'] for chunk in chunks]
            
            self.vector_store.add_vectors(vectors, metadata, ids)
            
            # Créer l'entrée d'index
            index_entry = {
                'filename': filename,
                'path': str(file_path),
                'upload_date': datetime.now().isoformat(),
                'page_count': len(doc),
                'chunk_count': len(chunks),
                'chunk_ids': ids
            }
            
            # Mettre à jour l'index
            self.index[filename] = index_entry
            self.save_index()
            
            return index_entry
            
        except Exception as e:
            # Nettoyer en cas d'erreur
            if doc:
                doc.close()
            if file_path.exists():
                try:
                    file_path.unlink()
                except PermissionError:
                    print("Impossible de supprimer le fichier, il sera nettoyé plus tard")
            raise e
        finally:
            if doc:
                doc.close()