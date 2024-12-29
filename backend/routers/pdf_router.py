from fastapi import APIRouter, File, UploadFile, HTTPException

router = APIRouter(prefix="/api/pdf", tags=["pdf"])

@router.post("/upload")
async def upload_pdf(file: UploadFile):
    if not file.content_type == "application/pdf":
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Pour le moment, on simule juste le succès
    return {"status": "success", "filename": file.filename}