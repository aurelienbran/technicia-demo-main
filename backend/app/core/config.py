import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env from backend directory
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

class Settings(BaseSettings):
    # API Keys
    ANTHROPIC_API_KEY: str
    VOYAGE_API_KEY: str
    
    # Model Configuration
    CLAUDE_MODEL: str = "claude-3-sonnet-20240229"
    MAX_TOKENS: int = 1024
    TEMPERATURE: float = 0.0
    
    # Infrastructure
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    COLLECTION_NAME: str = "technical_docs"
    VECTOR_SIZE: int = 1024
    
    # Application
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    
    # Processing Configuration
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100
    
    # Chemins
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    DOCS_PATH: str = os.path.join(BASE_DIR, "docs")
    STORAGE_PATH: str = os.path.join(BASE_DIR, "storage", "pdfs")
    INDEX_PATH: str = os.path.join(BASE_DIR, "storage", "index")
    
    def initialize_dirs(self):
        """Initialise les répertoires nécessaires."""
        os.makedirs(self.DOCS_PATH, exist_ok=True)
        os.makedirs(self.STORAGE_PATH, exist_ok=True)
        os.makedirs(self.INDEX_PATH, exist_ok=True)
    
    class Config:
        env_file = env_path
        env_file_encoding = 'utf-8'

settings = Settings()