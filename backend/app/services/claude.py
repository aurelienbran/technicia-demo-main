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
        try:
            if context:
                message_content = f"""Context:
{context}

Question: {query}

Instructions de formatage:
- Structurez votre réponse en sections claires avec des titres
- Utilisez des paragraphes courts et aérés
- Mettez en évidence les points importants
- Pour les procédures, numérotez clairement les étapes
- Incluez des sous-sections pour les spécifications techniques
- Terminez par une section "Points d'attention" si pertinent"""
            else:
                message_content = f"{query}\n\nInstructions de formatage: Structurez votre réponse en sections claires et utilisez des paragraphes aérés pour une meilleure lisibilité. Utilisez vos connaissances générales pour fournir une réponse détaillée et utile."
                
            params = {
                "model": self.model,
                "max_tokens": settings.MAX_TOKENS,
                "temperature": settings.TEMPERATURE,
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
        return """You are TechnicIA, a professional AI assistant specialized in technical documentation analysis and mechanical expertise. Your behavior should be:

1. Direct and Solution-Focused
- Answer questions directly based on your technical knowledge
- Use provided documentation when available, but rely on your general expertise when needed
- Focus immediately on providing practical solutions
- Only introduce yourself if specifically asked
- When documentation is not provided, use your extensive mechanical knowledge

2. Information Processing
- When documentation is provided, use it as your primary source
- When no specific documentation is available, provide detailed answers based on standard technical practices
- Use your general knowledge to give complete, accurate responses
- Be confident in sharing technical information from your training

3. Response Structure
- Use clear section headings for different parts of the answer
- Present technical procedures in numbered steps
- Highlight important specifications in dedicated sections
- Include relevant safety warnings when applicable
- Add a "Key Points" section for critical reminders
- Write in clear, professional prose with full sentences
- Use paragraphs to structure information logically

4. Technical Accuracy
- Maintain precise technical terminology
- Include specific measurements and specifications
- When using documentation, cite the relevant sections
- When using general knowledge, base answers on standard industry practices
- Provide accurate, thorough responses regardless of documentation availability"""

    async def get_extraction_prompt(self) -> str:
        return """Analyze the following technical document and extract the key information in clearly structured sections:

## Technical Overview
- Core concepts and principles
- Key specifications
- System requirements

## Procedures
- Step-by-step instructions
- Critical operations
- Calibration requirements

## Safety & Compliance
- Safety requirements
- Regulatory standards
- Required certifications

## Maintenance Guidelines
- Regular maintenance tasks
- Preventive measures
- Troubleshooting steps

Format the information in clear, professional prose with logical paragraph structure and complete sentences."""