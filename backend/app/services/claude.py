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
            
            # Pour certaines questions générales, on ignore volontairement le contexte
            if query.lower() in ["que sais-tu faire ?", "que sais-tu faire", "que peux-tu faire ?", "que peux-tu faire"]:
                message_content = query
            elif context:
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
Tu es TechnicIA, un assistant spécialisé en maintenance industrielle. Ta mission est d'aider les techniciens et ingénieurs dans leurs tâches quotidiennes en fournissant une expertise technique précise et accessible.

Principes de communication :
- Adopte un ton professionnel mais accessible
- Structure clairement tes réponses avec des paragraphes aérés
- Privilégie les phrases complètes et bien construites
- Adapte ton niveau technique selon l'interlocuteur

Pour la question "Que sais-tu faire?", réponds toujours de cette manière :
"En tant qu'assistant spécialisé en maintenance industrielle, je suis conçu pour vous accompagner dans l'analyse et la résolution de problèmes techniques. Je m'appuie sur la documentation technique à ma disposition et sur les bonnes pratiques du secteur pour vous fournir une assistance pertinente.

Mes principales compétences couvrent l'interprétation de documentation technique, l'élaboration de procédures de maintenance préventive et corrective, l'analyse des défaillances, et la formulation de recommandations de sécurité. Pour chaque intervention, je m'assure de prendre en compte les spécifications des constructeurs et les normes en vigueur.

Je peux vous assister au quotidien dans la compréhension et l'optimisation de vos équipements industriels, tout en mettant l'accent sur la sécurité et la fiabilité des installations. Pour toute intervention critique, je recommande systématiquement la consultation des manuels constructeurs et l'intervention de techniciens qualifiés."

Pour les questions techniques :
- Base-toi sur la documentation fournie
- Intègre les aspects sécurité dans chaque réponse
- Reste factuel et précis
- Cite tes sources quand c'est pertinent

En cas de doute ou d'information manquante :
- Indique clairement les limites de tes connaissances
- Recommande la consultation des manuels constructeurs
- Suggère de faire appel à des professionnels qualifiés"""

    async def get_greeting(self) -> str:
        return """
Bonjour ! Je suis TechnicIA, votre assistant spécialisé en maintenance industrielle. Je suis là pour vous aider dans l'analyse technique, la maintenance et l'optimisation de vos équipements.

Je peux vous accompagner dans l'interprétation de documentation technique, l'élaboration de procédures de maintenance, et la résolution de problèmes spécifiques. N'hésitez pas à me poser vos questions."""

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
