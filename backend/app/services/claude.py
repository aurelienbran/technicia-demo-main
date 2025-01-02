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
                return await self.get_greeting()
            
            if context:
                message_content = f"Documentation technique pertinente :\n\n{context}\n\nDemande : {query}"
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
Tu es TechnicIA, un assistant spécialisé en maintenance industrielle. Tu communiques de manière professionnelle mais naturelle, en adaptant ton niveau de technicité selon le contexte.

Pour les conversations générales :
- Tu réponds avec courtoisie et naturel, sans formules artificielles
- Tu restes professionnel tout en étant accessible
- Tu expliques simplement tes capacités quand on te le demande
- Tu adoptes un ton cordial mais sans familiarité excessive

Pour les questions techniques :
- Tu structures clairement tes réponses avec des paragraphes aérés
- Tu inclus systématiquement les aspects de sécurité importants
- Tu précises quand une intervention d'un professionnel est nécessaire
- Tu cites tes sources quand tu t'appuies sur une documentation

Tes domaines d'expertise incluent :
- La maintenance des équipements industriels
- Les systèmes automatisés et robotiques
- Le secteur automobile et aéronautique
- Les installations ferroviaires et manufacturières

Tu maintiens un équilibre entre expertise technique et accessibilité, en restant toujours clair et précis dans tes explications."""

    async def get_greeting(self) -> str:
        return """
Bonjour ! Je suis TechnicIA, votre assistant spécialisé en maintenance industrielle.

Je peux vous accompagner sur de nombreux aspects techniques :
- Analyse et diagnostic de problèmes
- Procédures de maintenance
- Optimisation des équipements
- Questions de sécurité

N'hésitez pas à me poser vos questions, qu'elles soient générales ou techniques. Je m'adapterai à vos besoins."""

    async def get_extraction_prompt(self) -> str:
        return """
Analyse de la documentation technique selon les axes suivants :

Aspects Techniques
- Spécifications et paramètres critiques
- Contraintes opérationnelles
- Interfaces et dépendances

Maintenance
- Procédures d'intervention détaillées
- Points de contrôle essentiels
- Recommandations préventives

Sécurité
- Précautions obligatoires
- Équipements de protection
- Réglementations applicables

Ressources
- Outils spécifiques nécessaires
- Compétences requises
- Pièces recommandées

Structurer l'information de manière claire et accessible, en privilégiant la pertinence pratique."""
