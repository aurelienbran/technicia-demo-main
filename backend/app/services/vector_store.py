import logging
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from ..core.config import settings

logger = logging.getLogger("technicia.vector_store")

class VectorStore:
    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        self._ensure_collection_exists()
        
    def _ensure_collection_exists(self):
        """Vérifie si la collection existe, la crée si nécessaire."""
        collections = self.client.get_collections()
        collection_names = [collection.name for collection in collections.collections]
        
        if settings.COLLECTION_NAME not in collection_names:
            self.client.create_collection(
                collection_name=settings.COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=settings.VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            logger.info(f"Collection {settings.COLLECTION_NAME} created")
        else:
            logger.info(f"Collection {settings.COLLECTION_NAME} exists")

    async def store_vectors(self, points: List[List[float]], metadata: List[Dict[str, Any]]) -> bool:
        """Stocke les vecteurs et leurs métadonnées dans Qdrant.
        
        Args:
            points: Liste de vecteurs d'embeddings
            metadata: Liste de métadonnées associées
            
        Returns:
            bool: True si le stockage a réussi
        """
        try:
            # Préparer les points avec leurs IDs et métadonnées
            qdrant_points = [
                models.PointStruct(
                    id=i,
                    vector=vector.tolist() if hasattr(vector, 'tolist') else vector,
                    payload=meta
                )
                for i, (vector, meta) in enumerate(zip(points, metadata))
            ]
            
            # Utiliser upsert pour ajouter ou mettre à jour les points
            self.client.upsert(
                collection_name=settings.COLLECTION_NAME,
                points=qdrant_points,
                wait=True  # Attendre la confirmation
            )
            
            logger.info(f"Stored {len(points)} vectors successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error storing vectors: {str(e)}")
            return False

    async def file_exists(self, file_path: str) -> bool:
        """Vérifie si un fichier a déjà été indexé."""
        try:
            result = self.client.scroll(
                collection_name=settings.COLLECTION_NAME,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(
                        key="filename",
                        match=models.MatchValue(value=file_path)
                    )]
                ),
                limit=1
            )
            return len(result[0]) > 0
        except Exception as e:
            logger.error(f"Error checking file existence: {str(e)}")
            return False