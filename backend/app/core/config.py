import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env from backend directory
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

DOCS_PATH = "C:\TechnicIADocs"

class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str
    VOYAGE_API_KEY: str
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
    DOCS_PATH: str = DOCS_PATH
    
    # Processing
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100
    STORAGE_PATH: str = "storage/pdfs"
    INDEX_PATH: str = "storage/index"

    class Config:
        env_file = env_path
        env_file_encoding = 'utf-8'

settings = Settings()