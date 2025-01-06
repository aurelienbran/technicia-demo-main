import logging
from typing import List, Dict, Any, Tuple
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
        self.ensure_collection_exists()
        self.log_collection_status()
    
    def ensure_collection_exists(self):
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

    def log_collection_status(self):
        try:
            points = self.client.scroll(
                collection_name=settings.COLLECTION_NAME,
                limit=100000
            )[0]
            
            logger.info(f"Collection '{settings.COLLECTION_NAME}' contains {len(points)} points")
            
            if points:
                logger.info("Sample of first 3 points:")
                for point in points[:3]:
                    logger.info(f"ID: {point.id}, Content: {point.payload.get('content', 'No content')[:100]}...")
                    
        except Exception as e:
            logger.error(f"Error checking collection status: {str(e)}")

    async def store_vectors(self, points: List[List[float]], metadata: List[Dict[str, Any]]) -> bool:
        try:
            qdrant_points = [
                models.PointStruct(
                    id=i,
                    vector=vector.tolist() if hasattr(vector, 'tolist') else vector,
                    payload=meta
                )
                for i, (vector, meta) in enumerate(zip(points, metadata))
            ]
            
            self.client.upsert(
                collection_name=settings.COLLECTION_NAME,
                points=qdrant_points,
                wait=True
            )
            
            logger.info(f"Stored {len(points)} vectors successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error storing vectors: {str(e)}")
            return False

    async def search(self, query_vector: List[float], limit: int = 5, score_threshold: float = 0.3) -> List[Dict[str, Any]]:
        try:
            results = self.client.search(
                collection_name=settings.COLLECTION_NAME,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )
            
            matches = [
                {
                    "score": hit.score,
                    "content": hit.payload.get("content", ""),
                    "source": hit.payload.get("filename", ""),
                    "page": hit.payload.get("page", 0),
                    "type": hit.payload.get("type", "unknown")
                }
                for hit in results
            ]
            
            if matches:
                logger.info(f"Found {len(matches)} matches. Best score: {matches[0]['score']}")
                logger.info(f"First match content: {matches[0]['content'][:100]}...")
            else:
                logger.info("No matches found")
                
            return sorted(matches, key=lambda x: x["score"], reverse=True)
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return []

    async def file_exists(self, file_path: str) -> bool:
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