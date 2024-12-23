from anthropic import AsyncAnthropic
from typing import List, Dict
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()

class ClaudeService:
    def __init__(self):
        self.client = AsyncAnthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
        self.model = os.getenv('CLAUDE_MODEL', 'claude-3-sonnet-20240229')
        
    def _format_context(self, context_chunks: List[Dict]) -> str:
        """Formate le contexte pour Claude"""
        formatted_chunks = []
        for chunk in context_chunks:
            context = f"Source: {chunk['filename']}, Page: {chunk['page_num']}\n"
            context += f"Texte: {chunk['text']}"
            if chunk.get('has_images', False):
                context += f"\n(Cette section contient {chunk['image_count']} image(s))"
            formatted_chunks.append(context)
        
        return "\n\n---\n\n".join(formatted_chunks)
        
    async def generate_response(self, query: str, context_chunks: List[Dict]) -> str:
        """Génère une réponse basée sur le contexte des documents"""
        if not context_chunks:
            return "Désolé, je n'ai pas trouvé d'information pertinente pour répondre à votre question."
        
        # Préparer le contexte
        context = self._format_context(context_chunks)
        
        # Construire le prompt
        system_prompt = """
Vous êtes un assistant technique spécialisé dans l'analyse de documentation technique. 
Votre rôle est de fournir des réponses précises et utiles basées sur la documentation fournie.

Directives:
1. Utilisez uniquement les informations du contexte fourni
2. Citez les sources spécifiques (noms de fichiers, numéros de page) quand pertinent
3. Si une information manque dans le contexte, indiquez-le clairement
4. Structurez vos réponses de manière claire et concise
5. Si des images sont mentionnées dans le contexte, intégrez cette information dans votre réponse
"""
        
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.2,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Sur la base de la documentation suivante:\n\n{context}\n\nQuestion: {query}"
                    }
                ]
            )
            
            return message.content
            
        except Exception as e:
            print(f"Erreur lors de la génération de la réponse: {str(e)}")
            return "Désolé, je n'ai pas pu générer une réponse. Veuillez réessayer."
    
    async def generate_summary(self, document_chunks: List[Dict]) -> str:
        """Génère un résumé d'un document"""
        if not document_chunks:
            return "Aucun contenu à résumer."
        
        context = self._format_context(document_chunks)
        
        system_prompt = """
Votre tâche est de créer un résumé clair et structuré de ce document technique.

Directives:
1. Identifiez les points clés et les concepts importants
2. Organisez l'information de manière logique
3. Mentionnez les sections contenant des illustrations ou schémas
4. Soyez concis tout en gardant les informations essentielles
5. Incluez les références aux sections importantes
"""
        
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.2,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": f"Veuillez créer un résumé du document suivant:\n\n{context}"
                    }
                ]
            )
            
            return message.content
            
        except Exception as e:
            print(f"Erreur lors de la génération du résumé: {str(e)}")
            return "Désolé, je n'ai pas pu générer un résumé. Veuillez réessayer."