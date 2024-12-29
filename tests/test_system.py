import unittest
from fastapi.testclient import TestClient
from typing import List, Dict
import json
import os

# Import your FastAPI app
from backend.main import app

class TestTechnicIA(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_pdf_path = "tests/data/sample.pdf"
        
    def test_health_check(self):
        """Test if the API is running"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_basic_query(self):
        """Test basic query endpoint"""
        response = self.client.post("/api/query", 
            json={"query": "test question"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("response", response.json())

    def test_pdf_upload(self):
        """Test PDF upload and processing"""
        with open(self.test_pdf_path, "rb") as pdf:
            response = self.client.post(
                "/api/pdf/upload",
                files={"file": ("test.pdf", pdf, "application/pdf")}
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.json())
        self.assertEqual(response.json()["status"], "success")

    def test_pdf_query(self):
        """Test querying indexed PDF content"""
        # First ensure we have a PDF indexed
        self.test_pdf_upload()
        
        # Then test querying it
        query = "What is in the test document?"
        response = self.client.post(
            "/api/query", 
            json={
                "query": query,
                "context": "test.pdf"
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("response", response.json())

    def test_error_handling(self):
        """Test error handling for invalid requests"""
        # Test invalid PDF
        response = self.client.post(
            "/api/pdf/upload",
            files={"file": ("test.txt", b"not a pdf", "text/plain")}
        )
        self.assertEqual(response.status_code, 400)
        
        # Test empty query
        response = self.client.post("/api/query", json={"query": ""})
        self.assertEqual(response.status_code, 400)

if __name__ == "__main__":
    unittest.main()