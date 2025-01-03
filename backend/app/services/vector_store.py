import logging
from qdrant_client import QdrantClient, models
from qdrant_client.http import models as rest
from qdrant_client.http.models import Distance, VectorParams

logger = logging.getLogger("technicia.vector_store")

class VectorStore:
    def __init__(self, client: QdrantClient, collection_name: str = "technical_docs"):
        self.client = client
        self.collection_name = collection_name
        self._ensure_collection()
        logger.info(f"Vector store initialized with collection: {collection_name}")

    def _ensure_collection(self):
        """Ensure the collection exists, create it if it doesn't."""
        collections = self.client.get_collections().collections
        exists = any(col.name == self.collection_name for col in collections)
        
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
            )
            logger.info(f"Created new collection: {self.collection_name}")
        else:
            logger.info(f"Collection {self.collection_name} already exists")

    def file_exists(self, file_path: str) -> bool:
        """Check if a file is already indexed in the vector store."""
        try:
            search_result = self.client.scroll(
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
            return len(search_result[0]) > 0
        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False

    async def add_texts(self, texts, metadatas, embeddings):
        """Add text embeddings to the vector store."""
        try:
            points = []
            for i, (text, metadata, embedding) in enumerate(zip(texts, metadatas, embeddings)):
                points.append(models.PointStruct(
                    id=metadata.get('chunk_id', f"point_{i}"),
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
            logger.error(f"Error adding texts to vector store: {e}")
            return False

    async def similarity_search(self, query_embedding, k=5):
        """Search for similar texts using the query embedding."""
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=k
            )
            return [(hit.payload, hit.score) for hit in results]
        except Exception as e:
            logger.error(f"Error during similarity search: {e}")
            return []