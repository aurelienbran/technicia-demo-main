# test_system.py

import asyncio
import logging
from pathlib import Path
import httpx
import json
import time

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('system_test.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("system_test")

class SystemTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": []
        }

    async def run_test(self, test_name: str, test_func):
        """Exécute un test et enregistre le résultat"""
        self.test_results["total_tests"] += 1
        start_time = time.time()
        
        try:
            await test_func()
            execution_time = time.time() - start_time
            self.test_results["passed_tests"] += 1
            status = "PASSED"
            logger.info(f"Test '{test_name}' passed in {execution_time:.2f}s")
        except Exception as e:
            execution_time = time.time() - start_time
            self.test_results["failed_tests"] += 1
            status = "FAILED"
            logger.error(f"Test '{test_name}' failed: {str(e)}")
            logger.exception(e)

        self.test_results["test_details"].append({
            "name": test_name,
            "status": status,
            "execution_time": f"{execution_time:.2f}s",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })

    async def test_health_check(self):
        """Test de l'endpoint /health"""
        response = await self.client.get(f"{self.base_url}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        logger.info("Health check data:", data)

    async def test_index_file(self):
        """Test de l'indexation d'un fichier"""
        pdf_path = Path("backend/docs/em.pdf")  # Modification du chemin ici
        
        with open(pdf_path, "rb") as f:
            files = {"file": (pdf_path.name, f, "application/pdf")}
            response = await self.client.post(
                f"{self.base_url}/api/index/file",
                files=files
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        logger.info("File indexing result:", data)

    async def test_query(self):
        """Test de requête"""
        test_queries = [
            "Quel est l'objectif principal du projet ?",
            "Quelles sont les fonctionnalités techniques ?",
            "Comment fonctionne le traitement du langage naturel ?"
        ]

        for query in test_queries:
            response = await self.client.post(
                f"{self.base_url}/api/query",
                json={
                    "query": query,
                    "limit": 5,
                    "score_threshold": 0.7
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "sources" in data
            logger.info(f"Query: {query}")
            logger.info(f"Answer: {data['answer'][:200]}...")
            logger.info(f"Sources used: {len(data['sources'])}")

    def save_results(self):
        """Sauvegarde les résultats des tests"""
        with open("test_results.json", "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

    async def run_all_tests(self):
        """Exécute tous les tests"""
        logger.info("Starting system tests...")
        
        test_scenarios = [
            ("Health Check", self.test_health_check),
            ("File Indexing", self.test_index_file),
            ("Query Processing", self.test_query)
        ]

        for test_name, test_func in test_scenarios:
            await self.run_test(test_name, test_func)

        await self.client.aclose()
        self.save_results()
        
        # Afficher le résumé
        logger.info("\n=== Test Results ===")
        logger.info(f"Total Tests: {self.test_results['total_tests']}")
        logger.info(f"Passed: {self.test_results['passed_tests']}")
        logger.info(f"Failed: {self.test_results['failed_tests']}")
        logger.info("==================\n")

async def main():
    tester = SystemTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
