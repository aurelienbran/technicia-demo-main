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
        self._log_collection_status()
    
    def _log_collection_status(self):
        try:
            response = self.client.get_collection(settings.COLLECTION_NAME)
            points_count = len(self.client.scroll(
                collection_name=settings.COLLECTION_NAME,
                limit=100000
            )[0])
            
            logger.info(f"Collection '{settings.COLLECTION_NAME}' contains {points_count} points")
            logger.info(f"First 3 points sample:")
            
            first_points = self.client.scroll(
                collection_name=settings.COLLECTION_NAME,
                limit=3
            )[0]
            
            for point in first_points:
                logger.info(f"Point ID: {point.id}, Content: {point.payload.get('content', 'No content')}")
                
        except Exception as e:
            logger.error(f"Error checking collection status: {str(e)}")
