from pydantic_settings import BaseSettings
from typing import Optional
import os
import sys

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
    VECTOR_SIZE: int = 1024
    
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
    DOCS_PATH: str = "C:\\TechnicIADocs"  # Chemin par défaut
    
    def get_docs_path(self) -> str:
        """Retourne le chemin absolu du dossier des documents."""
        if os.path.isabs(self.DOCS_PATH):
            return self.DOCS_PATH
        return os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), self.DOCS_PATH))
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

settings = Settings()