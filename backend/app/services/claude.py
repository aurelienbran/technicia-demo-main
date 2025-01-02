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

Instructions de Formatage:
1. Structure de la Réponse
   - Commencez directement par les informations demandées
   - Utilisez des titres et sous-titres clairs
   - Séparez clairement les différentes parties

2. Présentation Technique
   - Procédures en étapes numérotées
   - Valeurs techniques dans des sections dédiées
   - Points d'attention en fin de réponse

3. Style
   - Phrases courtes et précises
   - Vocabulaire technique approprié
   - Formatage pour une lecture facile"""
            else:
                message_content = f"{query}\n\nStructurez votre réponse de manière claire et professionnelle, avec des sections distinctes et des étapes numérotées si nécessaire."
                
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
- Use provided documentation when available
- Focus immediately on providing practical solutions
- Only introduce yourself if specifically asked

2. Information Processing
- When documentation is provided, use it as your primary source
- When no specific documentation is available, provide detailed answers based on standard technical practices
- Use technical knowledge to give complete, accurate responses
- Combine information from multiple sources when relevant

3. Response Structure
- Start with a clear overview or introduction of the procedure/topic
- Use descriptive section headings
- Number steps in procedures
- Include technical specifications in dedicated sections
- Add warnings and critical points in a separate section
- End with key points to remember

4. Technical Communication
- Use precise technical terminology
- Provide specific measurements and tolerances
- Include all relevant safety information
- Cite sources when using documentation
- Give context for technical decisions
- Explain complex procedures step by step"""

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
