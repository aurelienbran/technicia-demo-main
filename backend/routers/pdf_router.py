from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List, Dict
from services.pdf_service import PDFService
from pathlib import Path, WindowsPath
from pydantic import BaseModel

class DirectoryRequest(BaseModel):
    directory_path: str

class SearchRequest(BaseModel):
    query: str

router = APIRouter(prefix='/api/pdf')
pdf_service = PDFService()

@router.post('/upload')
async def upload_pdf(file: UploadFile = File(...)):
    """Upload et indexe un fichier PDF"""
    if not file.filename.endswith('.pdf'):
        return {'error': 'Le fichier doit être un PDF'}
    
    content = await file.read()
    result = await pdf_service.process_pdf(content, file.filename)
    return result

@router.post('/upload-directory')
async def upload_directory(request: DirectoryRequest):
    """Upload et indexe tous les PDFs d'un dossier"""
    try:
        path = Path(request.directory_path)
        abs_path = str(path.absolute())
        print(f"Processing directory: {abs_path}")
        
        # Vérifier si le dossier existe
        if not path.exists():
            raise HTTPException(status_code=400, detail=f"Le dossier {abs_path} n'existe pas")
        if not path.is_dir():
            raise HTTPException(status_code=400, detail=f"{abs_path} n'est pas un dossier")
            
        # Vérifier le contenu du dossier
        pdf_files = list(path.glob('**/*.pdf'))
        print(f"PDFs trouvés: {[f.name for f in pdf_files]}")
        
        if not pdf_files:
            raise HTTPException(status_code=400, detail=f"Aucun PDF trouvé dans {abs_path}")
        
        results = await pdf_service.process_directory(abs_path)
        return {
            'status': 'success',
            'directory': abs_path,
            'processed_files': results
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Erreur lors du traitement: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing directory: {str(e)}")

@router.get('/index-info')
def get_index_info() -> Dict:
    """Retourne des informations détaillées sur l'index"""
    try:
        info = pdf_service.get_index_info()
        return {
            'status': 'success',
            'info': info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/search')
def search_pdfs(request: SearchRequest):
    """Recherche dans le contenu des PDFs indexés"""
    try:
        if len(request.query.strip()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Le terme de recherche doit contenir au moins 3 caractères"
            )
        
        # Afficher l'état de l'index avant la recherche
        index_info = pdf_service.get_index_info()
        print(f"\nÉtat de l'index avant la recherche : {index_info}")
        
        results = pdf_service.search_content(request.query)
        return {
            'query': request.query,
            'indexed_files': index_info['total_files'],
            'results': results
        }
    except Exception as e:
        print(f"Erreur lors de la recherche: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/files', response_model=List[str])
def list_files():
    """Liste tous les fichiers PDF indexés"""
    return pdf_service.get_indexed_files()

@router.post('/clear')
def clear_storage():
    """Nettoie le stockage des PDFs"""
    pdf_service.clear_storage()
    return {'status': 'success', 'message': 'Storage cleared'}