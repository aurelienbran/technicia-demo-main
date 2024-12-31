from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams
import logging
from typing import List, Dict, Optional, Union
from ..core.config import settings

logger = logging.getLogger("technicia.vector_store")

class VectorStore:
    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        self.collection_name = settings.COLLECTION_NAME
        logger.info(f"Vector store initialized with collection: {self.collection_name}")

    async def init_collection(self) -> None:
        """
        Initialise ou réinitialise la collection.
        """
        try:
            # Vérifier si la collection existe
            collections = self.client.get_collections().collections
            exists = any(col.name == self.collection_name for col in collections)

            if exists:
                logger.info(f"Collection {self.collection_name} already exists")
                return

            # Créer la collection avec la configuration appropriée
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=settings.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )

            # Créer les index de payload
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="chunk_hash",
                field_schema="keyword"
            )

            logger.info(f"Collection {self.collection_name} created successfully")

        except Exception as e:
            logger.error(f"Error initializing collection: {str(e)}")
            raise

    async def add_vectors(
        self,
        vectors: List[List[float]],
        payloads: List[Dict],
        batch_size: int = 100
    ) -> None:
        """
        Ajoute des vecteurs et leurs métadonnées à la collection.
        """
        try:
            for i in range(0, len(vectors), batch_size):
                batch_vectors = vectors[i:i + batch_size]
                batch_payloads = payloads[i:i + batch_size]

                points = [
                    models.PointStruct(
                        id=idx + i,
                        vector=vector.tolist() if hasattr(vector, 'tolist') else vector,
                        payload=payload
                    )
                    for idx, (vector, payload) in enumerate(zip(batch_vectors, batch_payloads))
                ]

                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )

            logger.info(f"Successfully added {len(vectors)} vectors to collection")

        except Exception as e:
            logger.error(f"Error adding vectors: {str(e)}")
            raise

    async def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        score_threshold: float = 0.7,
        filter_conditions: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Recherche les documents les plus similaires.
        """
        try:
            # Traiter filter_conditions pour utiliser models.Filter
            if filter_conditions:
                final_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key=key,
                            match=models.MatchValue(value=value)
                        ) for key, value in filter_conditions.items()
                    ]
                )
            else:
                final_filter = None

            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=final_filter
            )

            results = []
            for scored_point in search_result:
                result = {
                    "score": scored_point.score,
                    "payload": scored_point.payload,
                    "id": scored_point.id
                }
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise

    async def search_by_hash(self, chunk_hash: str) -> List[Dict]:
        """
        Recherche des documents par leur hash.
        """
        try:
            filter_conditions = {"chunk_hash": chunk_hash}
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="chunk_hash",
                            match=models.MatchValue(value=chunk_hash)
                        )
                    ]
                ),
                limit=1
            )[0]
            
            return [{
                "id": point.id,
                "payload": point.payload
            } for point in results]
        except Exception as e:
            logger.error(f"Error searching by hash: {str(e)}")
            return []

    async def delete_vectors(self, ids: Union[List[int], List[str]]) -> None:
        """
        Supprime des vecteurs par leurs IDs.
        """
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=ids
                )
            )
            logger.info(f"Successfully deleted {len(ids)} vectors")
        except Exception as e:
            logger.error(f"Error deleting vectors: {str(e)}")
            raise

    async def get_collection_info(self) -> Dict:
        """
        Récupère les informations sur la collection.
        """
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "status": "active",
                "vector_size": settings.VECTOR_SIZE,
                "points_count": 0 if info is None else getattr(info, 'points_count', 0)
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            raise