import logging
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from ..core.config import settings

logger = logging.getLogger("technicia.vector_store")

class VectorStore:
    def __init__(self):
        self.client = QdrantClient(settings.QDRANT_HOST, port=settings.QDRANT_PORT)
        self.collection_name = "technical_docs"
        self.vector_size = 1024  # voyage-multimodal-3 dimension
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
            )
            logger.info(f"Collection {self.collection_name} created")
        else:
            logger.info(f"Collection {self.collection_name} exists")

    async def store_vectors(self, embeddings: List[List[float]], metadata: List[Dict[str, Any]]):
        if len(embeddings) != len(metadata):
            raise ValueError("Number of embeddings must match number of metadata items")

        points = [
            PointStruct(
                id=i,
                vector=embedding,
                payload=meta
            )
            for i, (embedding, meta) in enumerate(zip(embeddings, metadata))
        ]

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Stored {len(points)} vectors successfully")
        except Exception as e:
            logger.error(f"Error storing vectors: {str(e)}")
            raise

    async def search_vectors(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=0.7
            )

            return [{
                "score": hit.score,
                "metadata": hit.payload,
                "id": hit.id
            } for hit in results]
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise

    async def delete_collection(self):
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Collection {self.collection_name} deleted")
        except Exception as e:
            logger.error(f"Error deleting collection: {str(e)}")
            raise