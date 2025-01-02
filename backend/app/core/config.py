from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Keys et Configurations
    ANTHROPIC_API_KEY: str
    VOYAGE_API_KEY: str
    
    # Modèle Claude
    CLAUDE_MODEL: str = "claude-3-opus-20240229"
    MAX_TOKENS: int = 4096
    TEMPERATURE: float = 0.0
    
    # Configuration Serveur
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    
    # Chemins de Stockage
    STORAGE_PATH: str = "storage/pdfs"
    INDEX_PATH: str = "storage/index"
    
    # Configuration Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    COLLECTION_NAME: str = "technicia"
    VECTOR_SIZE: int = 1024
    
    # Paramètres d'indexation
    CHUNK_SIZE: int = 1500
    CHUNK_OVERLAP: int = 300
    
    class Config:
        env_file = ".env"
        extra = "allow"  # Permet des champs supplémentaires dans le fichier .env

settings = Settings()