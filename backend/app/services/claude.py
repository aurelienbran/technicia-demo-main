import logging
import anthropic
from typing import List, Dict, Any
from ..core.config import settings

logger = logging.getLogger("technicia.claude")

class ClaudeService:
    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=settings.ANTHROPIC_API_KEY
        )

    async def get_response(self, query: str, context: List[Dict[str, Any]]) -> str:
        try:
            # Construire le prompt avec le contexte
            context_str = "\n\n".join([f"Document: {c['source']} (Page {c['page']})\n{c['content']}" for c in context])
            
            prompt = f"Tu es TechnicIA, un assistant de documentation technique. Utilise le contexte suivant pour répondre à la question.\n\nContexte:\n{context_str}\n\nQuestion: {query}\n\nRéponds de manière claire et précise en utilisant uniquement les informations fournies dans le contexte. Si tu ne peux pas répondre avec certitude, dis-le."
            
            # Appeler Claude
            message = await self.client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=settings.MAX_TOKENS,
                temperature=settings.TEMPERATURE,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content
            
        except Exception as e:
            logger.error(f"Error getting Claude response: {str(e)}")
            raise