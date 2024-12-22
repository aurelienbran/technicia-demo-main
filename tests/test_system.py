import os
import asyncio
import logging
import httpx
import time
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("system_test")

class SystemTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.tests = [
            ("Health Check", self.test_health),
            ("Chat Query", self.test_chat_query)
        ]
        self.test_text = "How does a hydraulic system work?"

    async def run_test(self, test_name, test_func):
        try:
            start_time = time.time()
            await test_func()
            duration = time.time() - start_time
            logger.info(f"Test '{test_name}' passed in {duration:.2f}s")
            return True
        except Exception as e:
            logger.error(f"Test '{test_name}' failed: {str(e)}")
            logger.error(f"{e}")
            return False

    async def test_health(self):
        """Test the health check endpoint"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/")
            assert response.status_code == 200
            logger.info("Health check data:")
            logger.info(response.json())

    async def test_chat_query(self):
        """Test the chat query endpoint"""
        async with httpx.AsyncClient() as client:
            data = {
                "text": self.test_text,
                "max_tokens": 1000,
                "temperature": 0.7
            }
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=data
            )
            assert response.status_code == 200
            logger.info("Chat query response received successfully")
            logger.info(f"Query: {self.test_text}")
            logger.info(f"Response: {response.json()}")

    async def run_all_tests(self):
        logger.info("Starting system tests...")
        
        results = {
            "total": len(self.tests),
            "passed": 0,
            "failed": 0
        }

        for test_name, test_func in self.tests:
            if await self.run_test(test_name, test_func):
                results["passed"] += 1
            else:
                results["failed"] += 1

        logger.info("\n=== Test Results ===")
        logger.info(f"Total Tests: {results['total']}")
        logger.info(f"Passed: {results['passed']}")
        logger.info(f"Failed: {results['failed']}")
        logger.info("==================")

        return results

if __name__ == "__main__":
    test_suite = SystemTest()
    asyncio.run(test_suite.run_all_tests())