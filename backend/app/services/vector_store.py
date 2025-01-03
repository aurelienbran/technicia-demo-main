import logging
from qdrant_client import QdrantClient, models
from qdrant_client.http import models as rest
from qdrant_client.http.models import Distance, VectorParams
import random

logger = logging.getLogger("technicia.vector_store")

class VectorStore:
    def __init__(self, host="localhost", port=6333, collection_name="technical_docs"):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        collections = self.client.get_collections().collections
        exists = any(col.name == self.collection_name for col in collections)
        
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
            )
            logger.info(f"Created collection: {self.collection_name}")
        else:
            logger.info(f"Collection {self.collection_name} exists")

    async def file_exists(self, file_path: str) -> bool:
        try:
            result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="file_path",
                            match=models.MatchValue(value=file_path)
                        )
                    ]
                ),
                limit=1
            )
            return bool(result[0])
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False

    async def add_texts(self, texts, metadatas, embeddings):
        try:
            points = []
            for i, (text, metadata, embedding) in enumerate(zip(texts, metadatas, embeddings)):
                point_id = int(random.randint(1, 2**31-1))  # Generate numeric ID
                points.append(models.PointStruct(
                    id=point_id,
                    payload={
                        "text": text,
                        "file_path": metadata.get("file_path", ""),
                        "page": metadata.get("page", 0),
                        "chunk_index": metadata.get("chunk_index", 0)
                    },
                    vector=embedding
                ))
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            return True
        except Exception as e:
            logger.error(f"Error adding texts: {e}")
            return False

    async def similarity_search(self, query_embedding, k=5):
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=k
            )
            return [(hit.payload, hit.score) for hit in results]
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []