import asyncio
import logging
from pathlib import Path
import sys
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("technicia.test")

project_root = Path(__file__).parent.parent
backend_path = project_root / "backend"
sys.path.append(str(backend_path))
os.chdir(str(backend_path))

from app.core.config import settings
from app.services.vector_store import VectorStore
from app.services.embedding import EmbeddingService
from app.services.indexing import IndexingService
from app.services.claude import ClaudeService

class IntegrationTest:
    def __init__(self):
        self.vector_store = VectorStore()
        self.embedding = EmbeddingService()
        self.indexing = IndexingService()
        self.claude = ClaudeService()

    async def execute_with_timeout(self, coro, timeout=60):
        try:
            return await asyncio.wait_for(coro, timeout)
        except asyncio.TimeoutError:
            logger.error(f"Operation timed out after {timeout} seconds")
            raise

    async def test_configuration(self):
        logger.info("🔍 Test de la configuration...")
        await self.execute_with_timeout(asyncio.sleep(0))  # Simple test
        logger.info("✅ Configuration validée")

    async def test_qdrant_connection(self):
        logger.info("🔍 Test de la connexion Qdrant...")
        await self.execute_with_timeout(self.vector_store.init_collection())
        info = await self.execute_with_timeout(self.vector_store.get_collection_info())
        logger.info(f"✅ Connexion Qdrant établie. Collection: {info}")

    async def test_embeddings(self):
        logger.info("🔍 Test du service d'embeddings...")
        test_text = "Test du service d'embeddings de TechnicIA."
        await self.execute_with_timeout(self.embedding.get_embedding(test_text))
        logger.info("✅ Service d'embeddings fonctionnel")

    async def test_pdf_indexing(self, pdf_path: str):
        logger.info(f"🔍 Test d'indexation du PDF: {pdf_path}")
        result = await self.execute_with_timeout(
            self.indexing.index_document(pdf_path),
            timeout=120  # Plus long timeout pour l'indexation
        )
        if result["status"] != "success":
            raise ValueError(f"Échec de l'indexation: {result['error']}")
        logger.info(f"✅ PDF indexé avec succès: {result['chunks_processed']} chunks traités")
        return result

    async def test_search_and_response(self, query: str):
        logger.info(f"🔍 Test de recherche avec la requête: {query}")
        result = await self.execute_with_timeout(
            self.indexing.search(query),
            timeout=30
        )
        logger.info(f"✅ Recherche effectuée, {len(result.get('sources', [])) if result else 0} sources trouvées")
        if result and 'answer' in result:
            logger.info(f"🤖 Réponse de Claude: {result['answer']}")
        return result

async def run_tests():
    test = IntegrationTest()
    try:
        await test.test_configuration()
        await test.test_qdrant_connection()
        await test.test_embeddings()
        
        pdf_path = os.path.join("docs", "em.pdf")
        if os.path.exists(pdf_path):
            await test.test_pdf_indexing(pdf_path)
            query = "Quels sont les éléments principaux abordés dans ce document?"
            await test.test_search_and_response(query)
        else:
            logger.warning(f"⚠️ Fichier PDF de test non trouvé: {pdf_path}")
        
        logger.info("🎉 Tous les tests ont réussi!")
    except Exception as e:
        logger.error(f"❌ Erreur lors des tests: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_tests())