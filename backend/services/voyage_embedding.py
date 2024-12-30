import os
import voyageai
from typing import List, Dict

class VoyageEmbedding:
    def __init__(self):
        self.client = voyageai.Client()
        self.model = "voyage-2"

    async def get_embeddings(self, texts: List[str], type: str = "document") -> List[List[float]]:
        try:
            result = self.client.embed(
                texts,
                model=self.model,
                input_type=type
            )
            return result.embeddings
        except Exception as e:
            raise Exception(f"Erreur lors de la génération des embeddings: {str(e)}")