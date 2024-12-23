from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Dict, Optional
import os
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
                    size=self.vector_size,  # Dimension des vecteurs Voyage Multimodal-3
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

        points = [
            models.PointStruct(
                id=str(i) if ids is None else ids[i],
                vector=vector,
                payload=metadata[i]
            )
            for i, vector in enumerate(vectors)
        ]

        try:
            operation_info = self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            return [str(point.id) for point in points]
            
        except Exception as e:
            print(f"Erreur lors de l'ajout des vecteurs: {str(e)}")
            raise

    def search(self, query_vector: List[float], limit: int = 5) -> List[Dict]:
        """Recherche les documents les plus similaires"""
        if len(query_vector) != self.vector_size:
            raise ValueError(f"La dimension du vecteur de requête doit être {self.vector_size}")

        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit
            )

            return [
                {
                    'score': hit.score,
                    'metadata': hit.payload,
                    'id': hit.id
                }
                for hit in search_result
            ]
        except Exception as e:
            print(f"Erreur lors de la recherche: {str(e)}")
            return []

    def clear_collection(self):
        """Supprime tous les points de la collection"""
        try:
            self.client.delete_collection(self.collection_name)
            self._ensure_collection()
        except Exception as e:
            print(f"Erreur lors du nettoyage de la collection: {str(e)}")
            raise

    def get_collection_info(self) -> Dict:
        """Récupère les informations sur la collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                'vectors_count': collection_info.vectors_count,
                'indexed_vectors_count': collection_info.indexed_vectors_count,
                'status': collection_info.status
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des infos de collection: {str(e)}")
            return {
                'vectors_count': 0,
                'indexed_vectors_count': 0,
                'status': 'error'
            }