import logging
import voyageai
from ..core.config import settings

logger = logging.getLogger("technicia.embedding")

class EmbeddingService:
    def __init__(self):
        self.client = voyageai.Client(api_key=settings.VOYAGE_API_KEY)
        self.batch_size = 128
        logger.info("Embedding service initialized")

    async def get_embeddings(self, texts):
        try:
            all_embeddings = []
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                result = self.client.embed(
                    batch,
                    model="voyage-2",
                    input_type="document",
                    truncation=True
                )
                all_embeddings.extend(result.embeddings)
            return all_embeddings
        except Exception as e:
            logger.error(f"Error calling Voyage AI API: {e}")
            raise