from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Keys
    ANTHROPIC_API_KEY: str
    VOYAGE_API_KEY: str
    
    # Claude Configuration
    CLAUDE_MODEL: str = "claude-3-opus-20240229"
    MAX_TOKENS: int = 1024
    TEMPERATURE: float = 0.0
    
    # Qdrant Configuration
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    COLLECTION_NAME: str = "technical_docs"
    VECTOR_SIZE: int = 1024  # Voyage AI dimension
    
    # Chunking Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100
    
    # API Configuration
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    
    # Storage Configuration
    STORAGE_PATH: str = "storage/pdfs"
    INDEX_PATH: str = "storage/index"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Autoriser des champs supplémentaires dans le fichier .env
        extra = "allow"

settings = Settings()