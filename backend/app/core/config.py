import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Chargement explicite du .env
load_dotenv()

DOCS_PATH = "C:/TechnicIADocs"

class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str
    VOYAGE_API_KEY: str
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    DOCS_PATH: str = DOCS_PATH

    class Config:
        env_file = ".env"

settings = Settings()