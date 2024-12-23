from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Dict, Optional
import os
import uuid
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class VectorStore:
    def __init__(self):
        self.client = QdrantClient("localhost", port=6333)
        self.collection_name = "technicia_docs"
        self.vector_size = 1024  # Taille des vecteurs pour voyage-multimodal-3
        self._ensure_collection()

    def _ensure_collection(self):
        """Crée la collection si elle n'existe pas"""
        collections = self.client.get_collections().collections
        exists = any(col.name == self.collection_name for col in collections)

        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.vector_size,
                    distance=models.Distance.COSINE
                )
            )
            print(f"Collection {self.collection_name} créée avec dimension {self.vector_size}")

    def add_vectors(self, vectors: List[List[float]], metadata: List[Dict], ids: Optional[List[str]] = None) -> List[str]:
        """Ajoute des vecteurs à la collection avec leurs métadonnées"""
        if not vectors or not metadata:
            raise ValueError("Les listes de vecteurs et de métadonnées ne peuvent pas être vides")
            
        if len(vectors[0]) != self.vector_size:
            raise ValueError(f"La dimension des vecteurs doit être {self.vector_size}")

        # S'assurer que tous les IDs sont des UUID valides
        point_ids = [str(uuid.uuid4()) for _ in vectors] if ids is None else ids

        # Vérifier que tous les IDs sont valides
        for point_id in point_ids:
            try:
                uuid.UUID(point_id)
            except ValueError:
                raise ValueError(f"ID invalide: {point_id}. Les IDs doivent être des UUID valides.")

        points = [
            models.PointStruct(
                id=point_id,
                vector=vector.copy(),  # Copie pour éviter les modifications
                payload=meta.copy()
            )
            for point_id, vector, meta in zip(point_ids, vectors, metadata)
        ]

        try:
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True
            )
            return point_ids
            
        except Exception as e:
            print(f"Erreur lors de l'ajout des vecteurs: {str(e)}")
            raise

    def search(self, query_vector: List[float], limit: int = 5) -> List[Dict]:
        """Recherche les documents les plus similaires"""
        try:
            if len(query_vector) != self.vector_size:
                raise ValueError(f"La dimension du vecteur de requête doit être {self.vector_size}")

            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True
            )

            # Formater les résultats
            results = []
            for hit in search_result:
                result = {
                    'score': float(hit.score),  # Convertir en float Python standard
                    'id': str(hit.id),
                    'metadata': hit.payload
                }
                results.append(result)

            return results
            
        except Exception as e:
            print(f"Erreur lors de la recherche: {str(e)}")
            return []

    def clear_collection(self):
        """Supprime tous les points de la collection"""
        try:
            if self.collection_name in [c.name for c in self.client.get_collections().collections]:
                self.client.delete_collection(self.collection_name)
            self._ensure_collection()
        except Exception as e:
            print(f"Erreur lors du nettoyage de la collection: {str(e)}")

    def get_collection_info(self) -> Dict:
        """Récupère les informations sur la collection"""
        try:
            stats = self.client.get_collection(self.collection_name)
            return {
                "vectors_count": stats.vectors_count,
                "indexed_vectors_count": getattr(stats, 'indexed_vectors_count', 0),
                "status": getattr(stats, 'status', 'unknown')
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des infos de collection: {str(e)}")
            return {
                'vectors_count': 0,
                'indexed_vectors_count': 0,
                'status': 'error'
            }