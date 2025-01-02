from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Keys
    ANTHROPIC_API_KEY: str
    VOYAGE_API_KEY: str
    
    # Modèle Claude
    CLAUDE_MODEL: str = "claude-3-opus-20240229"
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.0
    
    # Configuration Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    COLLECTION_NAME: str = "technicia"
    VECTOR_SIZE: int = 1024
    
    # Paramètres d'indexation
    CHUNK_SIZE: int = 1500  # Taille augmentée pour plus de contexte
    CHUNK_OVERLAP: int = 300  # Chevauchement augmenté pour une meilleure continuité
    
    class Config:
        env_file = ".env"

settings = Settings()