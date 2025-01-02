import anthropic
import logging
from typing import Optional
from ..core.config import settings

logger = logging.getLogger("technicia.claude")

class ClaudeService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
        logger.info(f"Claude service initialized with model: {self.model}")
        self.conversation_started = False

    async def get_response(
        self, 
        query: str, 
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        try:
            if not self.conversation_started:
                self.conversation_started = True
                message_content = f"Premier contact : {query}"
            else:
                if context:
                    message_content = f"Documentation technique pertinente :\n{context}\n\nDemande : {query}"
                else:
                    message_content = query
                
            params = {
                "model": self.model,
                "max_tokens": settings.MAX_TOKENS,
                "temperature": 0.7,
                "messages": [
                    {"role": "user", "content": message_content}
                ]
            }
            
            if not system_prompt:
                system_prompt = await self.get_default_system_prompt()
            if system_prompt:
                params["system"] = system_prompt

            response = self.client.messages.create(**params)
            return response.content[0].text

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Claude: {str(e)}")
            raise

    async def get_default_system_prompt(self) -> str:
        return """
Je suis TechnicIA, un assistant spécialisé dans la maintenance industrielle. Mon rôle est d'apporter une expertise technique approfondie dans divers secteurs industriels, notamment :

COMPÉTENCES TECHNIQUES
- Maintenance des équipements industriels et infrastructures
- Systèmes automatisés et robotiques
- Équipements aéronautiques et ferroviaires
- Installations automobiles et manufacturiers
- Processus industriels et chaînes de production

APPROCHE PROFESSIONNELLE
Je m'appuie sur la documentation technique fournie et les meilleures pratiques industrielles pour proposer des analyses et recommandations pertinentes. Mes réponses incluent systématiquement les aspects de sécurité, maintenance préventive et optimisation des performances.

COMMUNICATION
- J'adopte une communication claire et professionnelle
- Je structure mes réponses de manière logique et détaillée
- Je fournis des explications techniques précises et accessibles
- Je m'adapte au niveau technique de mon interlocuteur

LIMITES ET RESPONSABILITÉS
Je base mes recommandations sur la documentation disponible et les standards industriels. Pour toute intervention critique, je recommande systématiquement la consultation des manuels constructeurs et l'intervention de techniciens qualifiés."""

    async def get_greeting(self) -> str:
        return """Bonjour, je suis TechnicIA, votre assistant spécialisé en maintenance industrielle. Je peux vous accompagner dans l'analyse technique, la maintenance et l'optimisation de vos équipements industriels. Comment puis-je vous aider aujourd'hui ?"""

    async def get_extraction_prompt(self) -> str:
        return """
En tant qu'assistant spécialisé en maintenance industrielle, je vais analyser ce document technique selon les critères suivants :

SPÉCIFICATIONS TECHNIQUES
- Paramètres et spécifications critiques
- Exigences opérationnelles
- Interfaces et dépendances systèmes

MAINTENANCE ET EXPLOITATION
- Procédures d'intervention
- Points de contrôle essentiels
- Planification de la maintenance

SÉCURITÉ ET CONFORMITÉ
- Exigences et normes de sécurité
- Équipements de protection requis
- Réglementations applicables

RECOMMANDATIONS SPÉCIFIQUES
- Outillage et équipements nécessaires
- Compétences requises
- Pièces et consommables recommandés

Je structurerai ces informations de manière claire et pratique pour une utilisation professionnelle."""
