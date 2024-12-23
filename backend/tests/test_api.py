import pytest
from fastapi.testclient import TestClient
from main import app
import json
from pathlib import Path

@pytest.fixture
def client():
    return TestClient(app)

# Tests des endpoints de base
def test_root_endpoint(client):
    """Test l'endpoint racine"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_ping_endpoint(client):
    """Test l'endpoint ping"""
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json()["message"] == "pong!"

# Tests des endpoints PDF
def test_pdf_upload(client):
    """Test l'upload d'un PDF"""
    # Créer un fichier PDF de test
    test_pdf_path = Path("test.pdf")
    test_pdf_path.write_bytes(b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>")
    
    with open(test_pdf_path, "rb") as f:
        response = client.post(
            "/api/pdf/upload",
            files={"file": ("test.pdf", f, "application/pdf")}
        )
    
    assert response.status_code == 200
    test_pdf_path.unlink()

def test_pdf_search(client):
    """Test la recherche dans les PDFs"""
    response = client.post(
        "/api/pdf/search",
        json={"query": "test search"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data

def test_list_files(client):
    """Test la liste des fichiers indexés"""
    response = client.get("/api/pdf/files")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

# Tests des endpoints de chat
def test_chat_query(client):
    """Test une requête de chat"""
    response = client.post(
        "/api/chat",
        json={
            "query": "Que fait ce système ?",
            "context_limit": 3
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "sources" in data

def test_document_summary(client):
    """Test la génération de résumé"""
    # D'abord uploader un PDF de test
    test_pdf_path = Path("test.pdf")
    test_pdf_path.write_bytes(b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>")
    
    with open(test_pdf_path, "rb") as f:
        upload_response = client.post(
            "/api/pdf/upload",
            files={"file": ("test.pdf", f, "application/pdf")}
        )
    
    # Ensuite tester le résumé
    response = client.post(f"/api/chat/summarize/test.pdf")
    
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "filename" in data
    
    test_pdf_path.unlink()

# Tests des cas d'erreur
def test_invalid_pdf_upload(client):
    """Test l'upload d'un fichier non-PDF"""
    test_file = Path("test.txt")
    test_file.write_text("Not a PDF")
    
    with open(test_file, "rb") as f:
        response = client.post(
            "/api/pdf/upload",
            files={"file": ("test.txt", f, "text/plain")}
        )
    
    assert response.status_code == 400
    test_file.unlink()

def test_empty_chat_query(client):
    """Test une requête de chat vide"""
    response = client.post(
        "/api/chat",
        json={"query": ""}
    )
    
    assert response.status_code == 400