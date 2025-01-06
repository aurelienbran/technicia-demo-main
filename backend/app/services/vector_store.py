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
            
    async def get_collection_info(self):
        try:
            info = self.client.get_collection(settings.COLLECTION_NAME)
            points_count = len(self.client.scroll(
                collection_name=settings.COLLECTION_NAME, 
                limit=1
            )[0])
            return {
                "name": settings.COLLECTION_NAME,
                "vector_size": settings.VECTOR_SIZE,
                "points_count": points_count
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            raise

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
            
            # Ajouter les logs
            logger.debug(f"Storing points: {len(qdrant_points)} vectors")
            for p in qdrant_points[:2]:  # Log quelques exemples
                logger.debug(f"Example point - ID: {p.id}, Vector size: {len(p.vector)}, Metadata: {p.payload}")
            
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

    async def search(self, query_vector: List[float], limit: int = 5, score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        try:
            # Log debug info
            logger.debug(f"Searching with vector size: {len(query_vector)}")
            
            # Vérifier le contenu de la collection
            info = await self.get_collection_info()
            logger.debug(f"Collection info before search: {info}")
            
            results = self.client.search(
                collection_name=settings.COLLECTION_NAME,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Log les résultats
            logger.debug(f"Search returned {len(results)} results")
            for r in results[:2]:  # Log quelques exemples
                logger.debug(f"Example result - Score: {r.score}, Payload: {r.payload}")
            
            matches = [
                {
                    "score": hit.score,
                    "metadata": hit.payload,
                    "content": hit.payload.get("content", "") if hit.payload else "",
                    "id": hit.id,
                    "source": hit.payload.get("filename", "") if hit.payload else "",
                    "page": hit.payload.get("page", 0) if hit.payload else 0
                }
                for hit in results
            ]
            
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