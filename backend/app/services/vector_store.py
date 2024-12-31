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
        logger.info(f"Vector store initialized with collection: {self.collection_name}")

    async def init_collection(self) -> None:
        """
        Initialise ou réinitialise la collection.
        """
        try:
            collections = self.client.get_collections().collections
            exists = any(col.name == self.collection_name for col in collections)

            if exists:
                logger.info(f"Collection {self.collection_name} already exists, recreating...")
                self.client.delete_collection(self.collection_name)

            # Créer la collection
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=settings.VECTOR_SIZE,
                    distance=Distance.COSINE  # Retour à COSINE pour Voyage AI
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=0  # Index immédiatement
                )
            )

            # Indexer le champ chunk_hash
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="chunk_hash",
                field_schema="keyword"
            )

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
                vector = np.array(vector, dtype=np.float32)
                # Les vecteurs Voyage AI sont déjà normalisés
                points.append(models.PointStruct(
                    id=self._collection_counter,
                    vector=vector.tolist(),
                    payload=payload
                ))
                self._collection_counter += 1

            logger.debug(f"Adding {len(points)} points to collection")
            logger.debug(f"First vector norm: {np.linalg.norm(points[0].vector)}")

            self.client.upsert(
                collection_name=self.collection_name,
                wait=True,
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
        score_threshold: float = 0.0,  # Seuil basé sur la distance cosinus
        filter_conditions: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Recherche les documents les plus similaires.
        Les vecteurs Voyage AI étant déjà normalisés, nous utilisons directement
        la similarité cosinus.
        """
        try:
            info = await self.get_collection_info()
            points_count = info['points_count']
            logger.info(f"Searching in collection with {points_count} points")
            
            if points_count == 0:
                logger.warning("Collection is empty")
                return []

            # Convertir en float32 pour cohérence
            query_vector = np.array(query_vector, dtype=np.float32).tolist()
            
            # Debug
            sample = np.array(query_vector[:5])
            logger.debug(f"Query vector sample: {sample}, norm: {np.linalg.norm(query_vector)}")

            # Effectuer la recherche avec un top-k plus large
            top_k = min(limit * 2, points_count)  # Double le nombre de résultats
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,  # Récupère plus de résultats
                score_threshold=0.0,  # Pas de seuil ici
                with_payload=True
            )

            # Log des résultats
            if not search_result:
                logger.warning("No results found")
            else:
                for i, point in enumerate(search_result[:5]):  # Log top 5
                    logger.info(f"Result {i+1}: score={point.score:.4f}")
                    if 'text' in point.payload:
                        preview = point.payload['text'][:100] + '...'
                        logger.debug(f"Text preview: {preview}")

            # Filtre et tri des résultats
            results = []
            for point in search_result:
                if point.score >= score_threshold:
                    results.append({
                        "score": float(point.score),
                        "payload": point.payload,
                        "id": point.id
                    })
                if len(results) >= limit:
                    break

            return results

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