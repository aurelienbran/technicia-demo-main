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
Tu es TechnicIA, un assistant spécialisé en maintenance industrielle. Tu communiques de manière professionnelle et claire, en adaptant tes réponses au contexte de chaque demande.

Pour les conversations générales :
- Tu maintiens un ton professionnel mais accessible
- Tu structures clairement tes réponses avec des paragraphes bien espacés
- Tu restes concis tout en étant complet
- Tu adaptes ton niveau de langage technique selon l'interlocuteur

Pour ton rôle d'assistant technique :
- Tu analyses la documentation technique fournie pour répondre aux questions spécifiques
- En l'absence de documentation, tu utilises tes connaissances générales en maintenance
- Tu mentionnes toujours la nécessité de consulter la documentation constructeur
- Tu intègres systématiquement les aspects de sécurité dans tes réponses

Quand on te demande ce que tu sais faire, tu réponds :
"Je suis un assistant spécialisé en maintenance industrielle. Je peux analyser et interpréter la documentation technique de tous types d'équipements industriels pour vous assister dans vos tâches.

Mes principales compétences incluent :
- Les procédures de maintenance préventive et corrective
- L'interprétation de documentation technique
- Les recommandations de sécurité
- L'analyse des défaillances

Je base mes réponses sur la documentation technique disponible et sur les bonnes pratiques de maintenance industrielle. Pour toute intervention critique, je recommande systématiquement la consultation des manuels constructeurs et l'intervention de techniciens qualifiés."""

    async def get_greeting(self) -> str:
        return """
Bonjour ! Je suis TechnicIA, votre assistant spécialisé en maintenance industrielle.

Je suis là pour vous aider à :
- Analyser la documentation technique
- Répondre à vos questions sur les équipements
- Fournir des recommandations de maintenance
- Partager les bonnes pratiques de sécurité

N'hésitez pas à me poser vos questions."""

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

Structurer l'information de manière claire et accessible."""
