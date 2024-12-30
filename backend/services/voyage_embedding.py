import os
import voyageai
from typing import List, Dict
from dotenv import load_dotenv

class VoyageEmbedding:
    def __init__(self):
        load_dotenv()
        voyageai.api_key = os.getenv("VOYAGE_API_KEY")
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