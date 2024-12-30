import fitz
from typing import List, Dict
import io
from PIL import Image

class PDFProcessor:
    def __init__(self):
        self.model = "voyage-multimodal-2"
        self.chunk_size = 1000
    
    def extract_content(self, pdf_path: str) -> List[Dict]:
        doc = fitz.open(pdf_path)
        contents = []
        
        for page in doc:
            # Extraire le texte
            text = page.get_text()
            if text.strip():
                contents.append({"type": "text", "content": text})
            
            # Extraire les images
            for img_index, img in enumerate(page.get_images()):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Convertir en PIL Image pour vérification
                image = Image.open(io.BytesIO(image_bytes))
                
                # Vérifier la qualité de l'image
                if image.size[0] > 100 and image.size[1] > 100:  # Ignorer les très petites images
                    contents.append({"type": "image", "content": image_bytes})
        
        return contents
    
    async def process_pdf(self, pdf_path: str) -> List[Dict]:
        contents = self.extract_content(pdf_path)
        processed_contents = []
        
        for content in contents:
            if content["type"] == "text":
                text = content["content"]
                chunks = [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size)]
                processed_contents.extend([{"type": "text", "content": chunk} for chunk in chunks])
            else:
                processed_contents.append(content)
                
        return processed_contents