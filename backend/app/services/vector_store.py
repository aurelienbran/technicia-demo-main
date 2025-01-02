from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
import logging
from typing import List, Dict, Optional, Union
from ..core.config import settings
import numpy as np

logger = logging.getLogger("technicia.vector_store")

class VectorStore:
    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        self.collection_name = settings.COLLECTION_NAME
        self._collection_counter = 0
        self._ensure_collection_exists()
        logger.info(f"Vector store initialized with collection: {self.collection_name}")

    def _ensure_collection_exists(self) -> None:
        try:
            collections = self.client.get_collections().collections
            exists = any(col.name == self.collection_name for col in collections)

            if not exists:
                logger.info(f"Creating collection {self.collection_name}...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=settings.VECTOR_SIZE,
                        distance=Distance.COSINE
                    ),
                    optimizers_config=models.OptimizersConfigDiff(
                        indexing_threshold=0
                    )
                )

                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="text",
                    field_schema="text"
                )
                
                logger.info(f"Collection {self.collection_name} created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")

        except Exception as e:
            logger.error(f"Error ensuring collection exists: {str(e)}")
            raise

    async def add_vectors(
        self,
        vectors: List[List[float]],
        payloads: List[Dict],
        batch_size: int = 100
    ) -> None:
        try:
            points = []
            for vector, payload in zip(vectors, payloads):
                vector = np.array(vector, dtype=np.float32)
                if 'text' not in payload:
                    logger.warning(f"Missing 'text' field in payload for point {self._collection_counter}")
                
                points.append(models.PointStruct(
                    id=self._collection_counter,
                    vector=vector.tolist(),
                    payload=payload
                ))
                self._collection_counter += 1

            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    wait=True,
                    points=batch
                )
                logger.debug(f"Added batch {i//batch_size + 1} of {(len(points)-1)//batch_size + 1}")

            logger.info(f"Successfully added {len(vectors)} vectors to collection")

        except Exception as e:
            logger.error(f"Error adding vectors: {str(e)}")
            raise

    async def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict]:
        try:
            info = await self.get_collection_info()
            points_count = info['points_count']
            logger.info(f"Searching in collection with {points_count} points")
            
            if points_count == 0:
                logger.warning("Collection is empty")
                return []

            query_vector = np.array(query_vector, dtype=np.float32).tolist()
            
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True
            )

            if not search_result:
                logger.warning("No results found")
                return []

            results = []
            for point in search_result:
                result = {
                    "score": float(point.score),
                    "payload": point.payload,
                    "id": point.id
                }
                if hasattr(point.payload, 'get'):
                    result["text"] = point.payload.get("text", "")
                    result["metadata"] = {
                        k: v for k, v in point.payload.items()
                        if k not in ["text"]
                    }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise

    async def get_collection_info(self) -> Dict:
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "status": "active",
                "vector_size": settings.VECTOR_SIZE,
                "points_count": getattr(info, 'points_count', 0),
                "indexed_percent": getattr(info, 'indexed_percent', 100)
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            raise