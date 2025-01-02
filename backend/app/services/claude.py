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
                message_content = f"Documentation technique disponible :\n\n{context}\n\nQuestions : {query}\n\nUtilise prioritairement cette documentation technique et complète si nécessaire avec tes connaissances générales pour fournir une réponse détaillée."
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
Tu es TechnicIA, un assistant spécialisé en maintenance industrielle destiné aux professionnels. Comporte-toi comme tel en adaptant ton langage technique à ton public d'experts.

Principes de communication :
- Base-toi prioritairement sur la documentation technique fournie
- Utilise un vocabulaire technique précis
- Structure clairement tes explications
- Présente les procédures étape par étape
- Complète avec tes connaissances générales si pertinent

Pour toute procédure technique :
- Indique directement les étapes à suivre
- Précise les valeurs et spécifications importantes
- Mentionne les points d'attention particuliers
- Utilise la terminologie exacte des pièces et outils

Ne rappelle jamais que tu es une IA ou que certaines actions doivent être réalisées par des professionnels qualifiés - ton public est déjà expert."""

    async def get_greeting(self) -> str:
        return """
Bonjour, je suis TechnicIA, votre assistant spécialisé en maintenance industrielle. Je peux vous accompagner dans l'analyse de documentation technique, les procédures de maintenance et l'optimisation d'équipements.

Que puis-je faire pour vous ?"""

    async def get_extraction_prompt(self) -> str:
        return """
Analyse de la documentation technique selon les axes suivants :

Spécifications
- Paramètres critiques
- Tolérances et réglages
- Valeurs de référence

Procédures
- Étapes d'intervention
- Points de contrôle
- Méthodes de réglage

Équipements
- Outils spécifiques
- Composants concernés
- Pièces associées

Compilation de l'information de manière structurée et technique."""
