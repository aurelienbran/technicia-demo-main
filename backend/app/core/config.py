import os
from pydantic_settings import BaseSettings

DOCS_PATH = "C:/TechnicIADocs"  # Nouveau chemin

class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str
    VOYAGE_API_KEY: str
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    DOCS_PATH: str = DOCS_PATH

settings = Settings()