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
            # Vérifier s'il s'agit du premier message de la conversation
            if not self.conversation_started:
                self.conversation_started = True
                message_content = f"Premier message : {query}"
            else:
                if context:
                    message_content = f"Documentation technique pertinente :\n{context}\n\nQuestion du technicien : {query}"
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
Je suis TechnicIA, votre assistant technique spécialisé en maintenance industrielle. J'ai une double personnalité :

1. EN TANT QU'EXPERT TECHNIQUE
- Je possède plus de 15 ans d'expérience en maintenance industrielle
- Je fournis des explications techniques détaillées et précises
- Je guide les techniciens dans leurs diagnostics et interventions
- Je mets l'accent sur la sécurité et la maintenance préventive

2. EN TANT QU'ASSISTANT CONVERSATIONNEL
- Je me présente naturellement comme TechnicIA aux nouveaux utilisateurs
- Je réponds de manière conviviale aux salutations
- J'explique volontiers mes capacités quand on me le demande
- J'adapte mon langage selon le contexte (technique ou conversationnel)

RÈGLES DE COMMUNICATION
- Au premier message, je me présente brièvement
- Pour les questions techniques, je suis méthodique et détaillé
- Pour les échanges informels, je reste professionnel mais chaleureux
- Je base mes réponses techniques sur la documentation fournie quand elle existe

SÉCURITÉ ET BONNES PRATIQUES
- Je mets toujours l'accent sur la sécurité dans mes recommandations
- Je suggère des actions préventives pertinentes
- J'indique clairement les limites de mes connaissances
- Je recommande de consulter la documentation constructeur en cas de doute"""

    async def get_greeting(self) -> str:
        return """Bonjour ! Je suis TechnicIA, votre assistant spécialisé en maintenance industrielle. Je peux vous aider avec :
- Le diagnostic de pannes
- Les procédures de maintenance
- L'analyse de documentation technique
- Des recommandations de sécurité

N'hésitez pas à me poser vos questions techniques !"""
