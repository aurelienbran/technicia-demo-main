from fastapi import APIRouter, HTTPException
from typing import List, Dict
from pydantic import BaseModel
from services.pdf_service import PDFService
from services.claude_service import ClaudeService

class ChatRequest(BaseModel):
    query: str
    context_limit: int = 5

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict]

router = APIRouter(prefix='/api/chat')
pdf_service = PDFService()
claude_service = ClaudeService()

@router.post('', response_model=ChatResponse)
async def chat_query(request: ChatRequest):
    """Traite une requête de chat en utilisant le contexte des documents"""
    try:
        # Rechercher le contexte pertinent
        context_chunks = pdf_service.search_content(request.query, limit=request.context_limit)
        
        if not context_chunks:
            return ChatResponse(
                response="Désolé, je n'ai pas trouvé d'informations pertinentes dans la documentation pour répondre à votre question.",
                sources=[]
            )
        
        # Générer la réponse avec Claude
        response = await claude_service.generate_response(request.query, context_chunks)
        
        # Formater les sources pour la réponse
        sources = [
            {
                'filename': chunk['filename'],
                'page': chunk['page_num'],
                'relevance': chunk['score']
            }
            for chunk in context_chunks
        ]
        
        return ChatResponse(
            response=response,
            sources=sources
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post('/summarize/{filename}')
async def summarize_document(filename: str):
    """Génère un résumé d'un document spécifique"""
    try:
        # Récupérer tous les chunks du document
        all_chunks = pdf_service.search_content(f"filename:{filename}", limit=100)
        
        if not all_chunks:
            raise HTTPException(
                status_code=404,
                detail=f"Document {filename} non trouvé ou non indexé"
            )
        
        # Générer le résumé
        summary = await claude_service.generate_summary(all_chunks)
        
        return {
            'filename': filename,
            'summary': summary
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))