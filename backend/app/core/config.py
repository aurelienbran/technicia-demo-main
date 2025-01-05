import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

DOCS_PATH = "C:\TechnicIADocs"

class Settings(BaseSettings):
    # Required settings
    ANTHROPIC_API_KEY: str
    VOYAGE_API_KEY: str
    CLAUDE_MODEL: str
    MAX_TOKENS: int
    TEMPERATURE: float
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    DOCS_PATH: str = DOCS_PATH
    COLLECTION_NAME: str = "technical_docs"
    VECTOR_SIZE: int = 1024
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100
    STORAGE_PATH: str = "storage/pdfs"
    INDEX_PATH: str = "storage/index"

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        env_file_encoding = 'utf-8'

settings = Settings()