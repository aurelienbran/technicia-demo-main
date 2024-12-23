from anthropic import Anthropic
from typing import List, Dict
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()

class ClaudeService:
    def __init__(self):
        self.client = Anthropic()
        self.model = os.getenv('CLAUDE_MODEL', 'claude-3-sonnet-20240229')
        
    def _prepare_context(self, context_chunks: List[Dict]) -> str:
        """Prépare le contexte à partir des chunks de texte"""
        formatted_chunks = []
        for chunk in context_chunks:
            formatted_chunk = f"""Source: {chunk['filename']}, Page: {chunk['page_num']}
            {chunk['text']}
            ---"""
            formatted_chunks.append(formatted_chunk)
            
        return "\n\n".join(formatted_chunks)
        
    async def generate_response(self, query: str, context_chunks: List[Dict]) -> str:
        """Génère une réponse basée sur le contexte des documents"""
        
        # Préparer le contexte pour Claude
        context = self._prepare_context(context_chunks)
        
        # Construire le prompt avec le contexte
        system_prompt = """
Vous êtes un assistant technique spécialisé en documentation technique. 
Votre rôle est de fournir des réponses précises et utiles basées sur la documentation fournie.

Veuillez :
- Utiliser uniquement les informations du contexte fourni
- Citer les sources spécifiques (numéros de page, noms de fichiers)
- Indiquer clairement si une information manque dans le contexte
- Structurer la réponse de manière claire et concise
- Utiliser des puces ou des numéros pour les étapes si nécessaire
"""
        
        human_prompt = f"""Sur la base de la documentation suivante :

{context}

Question : {query}"""
        
        try:
            # Créer le message avec Claude
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": human_prompt
                    }
                ]
            )
            
            # Retourner la réponse générée
            return message.content
            
        except Exception as e:
            print(f"Erreur lors de la génération de la réponse: {str(e)}")
            return "Désolé, je n'ai pas pu générer une réponse pour cette question. Veuillez réessayer."
    
    async def generate_summary(self, document_chunks: List[Dict]) -> str:
        """Génère un résumé d'un document basé sur ses chunks"""
        context = self._prepare_context(document_chunks)
        
        system_prompt = """
Votre tâche est de créer un résumé clair et structuré du document technique fourni.

Veuillez :
- Identifier les points clés et les concepts importants
- Organiser l'information de manière logique
- Être concis tout en conservant les informations essentielles
- Inclure les références aux sections importantes
"""
        
        human_prompt = f"""Veuillez créer un résumé du document suivant :

{context}"""
        
        try:
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": human_prompt
                    }
                ]
            )
            
            return message.content
            
        except Exception as e:
            print(f"Erreur lors de la génération du résumé: {str(e)}")
            return "Désolé, je n'ai pas pu générer un résumé pour ce document. Veuillez réessayer."