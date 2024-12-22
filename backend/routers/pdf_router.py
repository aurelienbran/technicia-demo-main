from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from services.pdf_service import PDFService
from pathlib import Path, WindowsPath
from pydantic import BaseModel

class DirectoryRequest(BaseModel):
    directory_path: str

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
        # Convertit le chemin en utilisant pathlib
        path = Path(request.directory_path)
        # Convertit en chemin absolu normalisé
        abs_path = str(path.absolute())
        print(f"Processing directory: {abs_path}")
        
        results = await pdf_service.process_directory(abs_path)
        return {
            'status': 'success',
            'directory': abs_path,
            'processed_files': results
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing directory: {str(e)}")

@router.get('/files', response_model=List[str])
def list_files():
    """Liste tous les fichiers PDF indexés"""
    return pdf_service.get_indexed_files()

@router.post('/clear')
def clear_storage():
    """Nettoie le stockage des PDFs"""
    pdf_service.clear_storage()
    return {'status': 'success', 'message': 'Storage cleared'}