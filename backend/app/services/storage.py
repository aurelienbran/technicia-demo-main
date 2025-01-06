import os
import stat
import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger("technicia.storage")

class StorageService:
    def __init__(self, docs_path: str):
        self.docs_path = Path(docs_path)
        self._ensure_directory()
    
    def _ensure_directory(self) -> None:
        """S'assure que le répertoire existe avec les bonnes permissions."""
        try:
            # Créer le répertoire s'il n'existe pas
            self.docs_path.mkdir(parents=True, exist_ok=True)
            
            # Définir les permissions pour le dossier
            os.chmod(self.docs_path, 
                    stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |  # Propriétaire
                    stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |  # Groupe
                    stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH)   # Autres
            
            logger.info(f"Directory configured with full permissions: {self.docs_path}")
        except Exception as e:
            logger.error(f"Error configuring directory: {str(e)}")
            raise
    
    def safe_read_file(self, file_path: Path) -> Optional[bytes]:
        """Lit un fichier de manière sécurisée en le copiant d'abord dans un dossier temporaire."""
        try:
            # Créer un chemin temporaire unique
            temp_dir = Path(self.docs_path) / ".temp"
            temp_dir.mkdir(exist_ok=True)
            
            temp_file = temp_dir / f"temp_{file_path.name}"
            
            # Copier le fichier
            shutil.copy2(file_path, temp_file)
            
            # Définir les permissions sur le fichier temporaire
            os.chmod(temp_file, 
                    stat.S_IRUSR | stat.S_IWUSR |  # Propriétaire
                    stat.S_IRGRP | stat.S_IWGRP |  # Groupe
                    stat.S_IROTH)                   # Autres (lecture seule)
            
            # Lire le contenu
            with open(temp_file, 'rb') as f:
                content = f.read()
            
            # Nettoyer
            os.remove(temp_file)
            
            return content
            
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
        
    def check_permissions(self, path: Path) -> dict:
        """Vérifie et retourne les informations sur les permissions."""
        try:
            stat_info = os.stat(path)
            return {
                "path": str(path),
                "exists": path.exists(),
                "is_file": path.is_file(),
                "mode": oct(stat_info.st_mode)[-3:],
                "uid": stat_info.st_uid,
                "gid": stat_info.st_gid,
                "size": stat_info.st_size if path.is_file() else None
            }
        except Exception as e:
            logger.error(f"Error checking permissions for {path}: {str(e)}")
            return {}