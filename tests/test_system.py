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
            logger.info(f"Starting test: {test_name}")
            start_time = time.time()
            await test_func()
            duration = time.time() - start_time
            logger.info(f"Test '{test_name}' passed in {duration:.2f}s")
            return True
        except Exception as e:
            logger.error(f"Test '{test_name}' failed: {str(e)}")
            logger.error(f"Error details: {type(e).__name__}")
            return False

    async def test_health(self):
        """Test the health check endpoint"""
        try:
            logger.info(f"Sending GET request to {self.base_url}/")
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/")
                response.raise_for_status()  # Raise exception for bad status codes
                logger.info("Health check data:")
                logger.info(response.json())
        except httpx.ConnectError:
            logger.error(f"Unable to connect to {self.base_url}. Is the server running?")
            raise
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise

    async def test_chat_query(self):
        """Test the chat query endpoint"""
        try:
            data = {
                "query": self.test_text,
                "limit": 5,
                "score_threshold": 0.7
            }
            logger.info(f"Sending POST request to {self.base_url}/api/query")
            logger.info(f"Request data: {data}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/query",
                    json=data
                )
                response.raise_for_status()
                logger.info("Chat query response received successfully")
                logger.info(f"Query: {self.test_text}")
                logger.info(f"Response: {response.json()}")
        except httpx.ConnectError:
            logger.error(f"Unable to connect to {self.base_url}/api/query. Is the server running?")
            raise
        except Exception as e:
            logger.error(f"Chat query failed: {str(e)}")
            raise

    async def run_all_tests(self):
        logger.info("Starting system tests...")
        logger.info(f"Testing API at: {self.base_url}")
        
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