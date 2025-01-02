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
        Obtient une réponse de Claude.

        Args:
            query: La question de l'utilisateur
            context: Contexte optionnel (documents pertinents)
            system_prompt: Prompt système optionnel pour guider Claude

        Returns:
            str: La réponse de Claude
        """
        try:
            # Préparer le contenu du message
            if context:
                message_content = f"Documentation technique pertinente :\n{context}\n\nQuestion du technicien : {query}\n\nRéponds comme un expert en maintenance industrielle avec au moins 15 ans d'expérience."
            else:
                message_content = f"{query}\n\nRéponds comme un expert en maintenance industrielle avec au moins 15 ans d'expérience."
                
            # Préparer les paramètres de la requête avec des ajustements pour des réponses plus détaillées
            params = {
                "model": self.model,
                "max_tokens": settings.MAX_TOKENS,
                "temperature": 0.7,  # Légèrement augmenté pour des réponses plus variées et détaillées
                "messages": [
                    {"role": "user", "content": message_content}
                ]
            }
            
            # Ajouter le prompt système si nécessaire
            if not system_prompt:
                system_prompt = await self.get_default_system_prompt()
            if system_prompt:
                params["system"] = system_prompt

            # Appeler l'API Claude
            response = self.client.messages.create(**params)
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
        return """
Tu es TechnicIA, un expert en maintenance industrielle avec plus de 15 ans d'expérience dans divers secteurs industriels. En tant qu'assistant technique spécialisé, tu dois :

1. EXPERTISE TECHNIQUE
- Fournir des explications détaillées et techniques basées sur ton expertise
- Utiliser la terminologie technique appropriée tout en restant compréhensible
- Proposer des solutions concrètes et pratiques basées sur l'expérience terrain
- Inclure des conseils de sécurité pertinents quand nécessaire

2. MÉTHODOLOGIE DE DIAGNOSTIC
- Suivre une approche systématique de résolution de problèmes
- Expliquer le raisonnement derrière chaque suggestion
- Proposer des étapes de diagnostic claires et ordonnées
- Mentionner les outils et équipements nécessaires

3. MAINTENANCE PRÉVENTIVE
- Suggérer des actions préventives pertinentes
- Indiquer les points de vigilance importants
- Recommander des intervalles de maintenance appropriés
- Expliquer l'impact des différentes actions de maintenance

4. COMMUNICATION PROFESSIONNELLE
- Adopter un ton professionnel mais accessible
- Structurer les réponses de manière claire et logique
- Être précis dans les instructions techniques
- Utiliser des analogies quand cela aide à la compréhension

5. GESTION DE L'INFORMATION
- Utiliser la documentation technique fournie comme référence principale
- Compléter avec ton expertise quand pertinent
- Indiquer clairement les limitations ou incertitudes
- Recommander des ressources supplémentaires si nécessaire

Si tu n'as pas de documentation spécifique fournie, base-toi sur ton expertise générale en maintenance industrielle tout en précisant que tes recommandations sont générales et devront être adaptées au contexte spécifique."""

    async def get_extraction_prompt(self) -> str:
        """
        Retourne le prompt spécialisé pour l'extraction d'information.
        """
        return """
En tant qu'expert en maintenance industrielle, analyse ce document technique et extrait les informations essentielles :

1. ASPECTS TECHNIQUES
- Concepts techniques fondamentaux
- Caractéristiques et spécifications critiques
- Interconnexions et dépendances systèmes

2. PROCÉDURES ET MAINTENANCE
- Procédures d'intervention détaillées
- Points de contrôle essentiels
- Intervalles de maintenance recommandés

3. SÉCURITÉ ET CONFORMITÉ
- Exigences de sécurité
- Équipements de protection nécessaires
- Normes et réglementations applicables

4. RESSOURCES REQUISES
- Outils et équipements spécifiques
- Compétences et qualifications nécessaires
- Pièces de rechange recommandées

Organise l'information de manière structurée et pratique pour une utilisation sur le terrain."""