import logging
import voyageai

logger = logging.getLogger("technicia.embedding")

class EmbeddingService:
    def __init__(self):
        self.client = voyageai.Client()
        logger.info("Embedding service initialized")

    async def get_embeddings(self, texts):
        try:
            result = self.client.embed(
                texts,
                model="voyage-2",
                input_type="document",
                truncation=True
            )
            return result.embeddings
        except Exception as e:
            logger.error(f"Error calling Voyage AI API: {e}")
            raise