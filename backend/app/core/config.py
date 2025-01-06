import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env from backend directory
_env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(str(_env_path))

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
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    DOCS_PATH: str = str(BASE_DIR / "docs")
    
    def initialize_dirs(self):
        """Initialise les répertoires nécessaires."""
        Path(self.DOCS_PATH).mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = str(_env_path)
        env_file_encoding = 'utf-8'

settings = Settings()