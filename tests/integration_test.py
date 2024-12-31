import asyncio
import logging
from pathlib import Path
import sys
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("technicia.test")

# Ajout du chemin backend au PYTHONPATH
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

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

    async def test_configuration(self):
        """Vérifie la configuration de l'environnement"""
        logger.info("🔍 Test de la configuration...")
        
        required_vars = [
            'ANTHROPIC_API_KEY',
            'VOYAGE_API_KEY',
            'QDRANT_HOST',
            'QDRANT_PORT'
        ]
        
        for var in required_vars:
            value = getattr(settings, var)
            if not value:
                raise ValueError(f"Variable d'environnement manquante: {var}")
        
        logger.info("✅ Configuration validée")

    async def test_qdrant_connection(self):
        """Vérifie la connexion à Qdrant"""
        logger.info("🔍 Test de la connexion Qdrant...")
        
        try:
            await self.vector_store.init_collection()
            collection_info = await self.vector_store.get_collection_info()
            logger.info(f"✅ Connexion Qdrant établie. Collection: {collection_info}")
        except Exception as e:
            raise Exception(f"Erreur de connexion Qdrant: {str(e)}")

    async def test_embeddings(self):
        """Vérifie le service d'embeddings"""
        logger.info("🔍 Test du service d'embeddings...")
        
        test_text = "Ceci est un test du service d'embeddings de TechnicIA."
        try:
            embedding = await self.embedding.get_embedding(test_text)
            if len(embedding) != settings.VECTOR_SIZE:
                raise ValueError(f"Dimension d'embedding incorrecte: {len(embedding)}")
            logger.info("✅ Service d'embeddings fonctionnel")
        except Exception as e:
            raise Exception(f"Erreur du service d'embeddings: {str(e)}")

    async def test_pdf_indexing(self, pdf_path: str):
        """Teste l'indexation d'un PDF"""
        logger.info(f"🔍 Test d'indexation du PDF: {pdf_path}")
        
        try:
            result = await self.indexing.index_document(pdf_path)
            if result["status"] != "success":
                raise ValueError(f"Échec de l'indexation: {result['error']}")
            logger.info(f"✅ PDF indexé avec succès: {result['chunks_processed']} chunks traités")
            return result
        except Exception as e:
            raise Exception(f"Erreur d'indexation PDF: {str(e)}")

    async def test_search_and_response(self, query: str):
        """Teste la recherche et la génération de réponse"""
        logger.info(f"🔍 Test de recherche avec la requête: {query}")
        
        try:
            result = await self.indexing.search(query)
            logger.info(f"✅ Recherche effectuée, {len(result['sources'])} sources trouvées")
            logger.info(f"🤖 Réponse de Claude: {result['answer']}")
            return result
        except Exception as e:
            raise Exception(f"Erreur de recherche/réponse: {str(e)}")

async def run_tests():
    """Exécute tous les tests d'intégration"""
    test = IntegrationTest()
    
    try:
        # Test de la configuration
        await test.test_configuration()
        
        # Test de Qdrant
        await test.test_qdrant_connection()
        
        # Test des embeddings
        await test.test_embeddings()
        
        # Test de l'indexation PDF (si un fichier est fourni)
        pdf_path = os.path.join("backend", "docs", "test.pdf")
        if os.path.exists(pdf_path):
            await test.test_pdf_indexing(pdf_path)
            
            # Test de recherche
            query = "Quel est le sujet principal de ce document?"
            await test.test_search_and_response(query)
        else:
            logger.warning(f"⚠️ Fichier PDF de test non trouvé: {pdf_path}")
        
        logger.info("🎉 Tous les tests ont réussi!")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors des tests: {str(e)}")
        raise

if __name__ == "__main__":
    # Création des dossiers nécessaires
    os.makedirs("backend/docs", exist_ok=True)
    os.makedirs("storage/pdfs", exist_ok=True)
    os.makedirs("storage/index", exist_ok=True)
    
    # Exécution des tests
    asyncio.run(run_tests())