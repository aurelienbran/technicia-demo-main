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
        self._collection_counter = 0  # Compteur pour les IDs
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
                logger.info(f"Collection {self.collection_name} already exists, recreating...")
                self.client.delete_collection(self.collection_name)

            # Créer la collection avec la configuration appropriée
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=settings.VECTOR_SIZE,
                    distance=Distance.DOT
                )
            )

            # Créer les index de payload
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="chunk_hash",
                field_schema="keyword"
            )

            # Réinitialiser le compteur
            self._collection_counter = 0

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
            points = []
            for vector, payload in zip(vectors, payloads):
                # Normaliser le vecteur
                vector = np.array(vector)
                norm = np.linalg.norm(vector)
                vector = vector / norm

                # Créer le point
                points.append(models.PointStruct(
                    id=self._collection_counter,
                    vector=vector.tolist(),
                    payload=payload
                ))
                self._collection_counter += 1

            # Logger les détails
            logger.debug(f"Adding {len(points)} points to collection")
            for point in points:
                logger.debug(f"Point {point.id}: {len(point.vector)} dimensions, hash: {point.payload.get('chunk_hash')}")

            # Ajouter les points
            self.client.upsert(
                collection_name=self.collection_name,
                wait=True,  # Attendre que les points soient indexés
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
        score_threshold: float = 0.3,
        filter_conditions: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Recherche les documents les plus similaires.
        """
        try:
            # Vérifier que la collection existe
            info = await self.get_collection_info()
            points_count = info['points_count']
            logger.info(f"Searching in collection with {points_count} points")
            
            if points_count == 0:
                logger.warning("Collection is empty")
                return []

            # Normaliser le vecteur de requête
            query_vector = np.array(query_vector)
            query_vector = query_vector / np.linalg.norm(query_vector)

            # Recherche
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector.tolist(),
                limit=limit,
                score_threshold=score_threshold,
                with_payload=True,
                with_vectors=True
            )

            # Log détaillé des résultats
            if not search_result:
                logger.warning("No results found above threshold")
            else:
                for i, point in enumerate(search_result):
                    logger.info(f"Result {i+1}: score={point.score:.4f}, text_length={len(point.payload.get('text', ''))}")

            return [{
                "score": point.score,
                "payload": point.payload,
                "id": point.id
            } for point in search_result]

        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise

    async def search_by_hash(self, chunk_hash: str) -> List[Dict]:
        """
        Recherche des documents par leur hash.
        """
        try:
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
                limit=1,
                with_payload=True
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
                "points_count": getattr(info, 'points_count', 0)
            }
        except Exception as e:
            logger.error(f"Error getting collection info: {str(e)}")
            raise