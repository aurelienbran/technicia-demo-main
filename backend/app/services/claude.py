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

    async def get_response(
        self, 
        query: str, 
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Obtient une réponse de Claude en utilisant l'API messages.

        Args:
            query: La question de l'utilisateur
            context: Contexte optionnel (documents pertinents)
            system_prompt: Prompt système optionnel pour guider Claude

        Returns:
            str: La réponse de Claude
        """
        try:
            messages = []

            # Ajouter le prompt système si fourni
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            # Construire le message utilisateur avec contexte si disponible
            user_content = query
            if context:
                user_content = f"Context:\n{context}\n\nQuestion: {query}"

            messages.append({
                "role": "user",
                "content": user_content
            })

            # Appeler l'API Claude
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=settings.MAX_TOKENS,
                temperature=settings.TEMPERATURE,
                messages=messages
            )

            return response.content[0].text

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Claude: {str(e)}")
            raise

    async def get_default_system_prompt(self) -> str:
        """
        Retourne le prompt système par défaut pour TechnicIA.
        """
        return """You are TechnicIA, an expert AI assistant specializing in technical documentation analysis and interpretation.
Your role is to:
1. Provide clear, accurate answers based on the technical documentation provided
2. Help users understand complex technical concepts and procedures
3. Be direct and concise in your responses while remaining thorough
4. Acknowledge when specific information is not available in the provided context

Always base your answers on the context provided. If no context is provided, clearly state that you need specific documentation to provide accurate information."""

    async def get_extraction_prompt(self) -> str:
        """
        Retourne le prompt spécialisé pour l'extraction d'information des documents techniques.
        """
        return """Analyze the following technical document and extract the key information:
- Main technical concepts
- Important procedures
- Critical specifications
- Safety requirements (if any)
- Dependencies and requirements

Format the information in a clear, structured way."""