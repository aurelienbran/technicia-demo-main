import os
import voyageai
from typing import List, Dict, Union
from dotenv import load_dotenv

class VoyageEmbedding:
    def __init__(self):
        load_dotenv()
        voyageai.api_key = os.getenv("VOYAGE_API_KEY")
        self.client = voyageai.Client()
        self.model = "voyage-multimodal-2"

    async def get_embeddings(self, contents: List[Dict]) -> List[List[float]]:
        try:
            embeddings = []
            for content in contents:
                if content["type"] == "text":
                    result = self.client.embed(
                        [content["content"]],
                        model=self.model,
                        input_type="document"
                    )
                    embeddings.append(result.embeddings[0])
                else:  # type == "image"
                    result = self.client.embed(
                        content["content"],
                        model=self.model,
                        input_type="image"
                    )
                    embeddings.append(result.embeddings[0])
            return embeddings
        except Exception as e:
            raise Exception(f"Erreur lors de la génération des embeddings: {str(e)}")