import os
import stat
import logging
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

logger = logging.getLogger("technicia.config")

# Load .env from backend directory
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

DOCS_PATH = "C:\\TechnicIADocs"

def ensure_directory_permissions(path: str) -> None:
    """S'assure que le répertoire existe avec les bonnes permissions."""
    try:
        os.makedirs(path, exist_ok=True)
        # Définir des permissions complètes (lecture/écriture/exécution)
        os.chmod(path, 
                stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |  # Propriétaire
                stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |  # Groupe
                stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)   # Autres
        logger.info(f"Directory configured with full permissions: {path}")
    except Exception as e:
        logger.error(f"Error configuring directory permissions: {str(e)}")
        raise

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
    
    def initialize_directories(self):
        """Initialise tous les répertoires nécessaires avec les bonnes permissions."""
        ensure_directory_permissions(self.DOCS_PATH)
        ensure_directory_permissions(self.STORAGE_PATH)
        ensure_directory_permissions(self.INDEX_PATH)

    class Config:
        env_file = env_path
        env_file_encoding = 'utf-8'

settings = Settings()
