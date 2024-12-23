import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json
import os
import shutil
from PIL import Image
import io
from backend.main import app

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture
def sample_image():
    """Crée une image de test"""
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

@pytest.fixture
def sample_pdf_with_image(sample_image):
    """Crée un PDF de test avec image"""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test PDF with image")
    img_rect = fitz.Rect(100, 100, 200, 200)
    page.insert_image(img_rect, stream=sample_image)
    
    pdf_path = Path('test_with_image.pdf')
    doc.save(str(pdf_path))
    doc.close()
    
    with open(pdf_path, 'rb') as f:
        content = f.read()
    
    pdf_path.unlink()
    return content

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup - créer les dossiers nécessaires
    test_storage = Path('test_storage')
    test_storage.mkdir(exist_ok=True)
    
    yield
    
    # Teardown - nettoyer
    if test_storage.exists():
        shutil.rmtree(test_storage)
    
    files_to_clean = ['test.pdf', 'test.txt', 'test_with_image.pdf']
    for file in files_to_clean:
        if os.path.exists(file):
            os.remove(file)

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
def test_pdf_upload_with_text_only(client):
    """Test l'upload d'un PDF text only"""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Test PDF content")
    
    pdf_path = Path("test.pdf")
    doc.save(str(pdf_path))
    doc.close()
    
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/pdf/upload",
            files={"file": ("test.pdf", f, "application/pdf")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    assert 'details' in data

def test_pdf_upload_with_image(client, sample_pdf_with_image):
    """Test l'upload d'un PDF avec image"""
    pdf_path = Path("test_with_image.pdf")
    pdf_path.write_bytes(sample_pdf_with_image)
    
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/pdf/upload",
            files={"file": ("test_with_image.pdf", f, "application/pdf")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'success'
    assert 'details' in data
    # Vérifier que l'indexation a bien pris en compte l'image
    assert data['details'].get('chunk_count', 0) > 0

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
    assert "doit être un PDF" in response.json()['detail']

def test_pdf_search_with_results(client, sample_pdf_with_image):
    """Test la recherche avec résultats"""
    # D'abord uploader un PDF
    pdf_path = Path("test_with_image.pdf")
    pdf_path.write_bytes(sample_pdf_with_image)
    
    with open(pdf_path, "rb") as f:
        upload_response = client.post(
            "/api/pdf/upload",
            files={"file": ("test_with_image.pdf", f, "application/pdf")}
        )
    
    assert upload_response.status_code == 200
    
    # Maintenant faire une recherche
    search_response = client.post(
        "/api/pdf/search",
        json={"query": "Test PDF with image"}
    )
    
    assert search_response.status_code == 200
    results = search_response.json()
    assert len(results.get('results', [])) > 0

def test_pdf_search_no_results(client):
    """Test la recherche sans résultats"""
    response = client.post(
        "/api/pdf/search",
        json={"query": "Something that doesn't exist"}
    )
    
    assert response.status_code == 200
    results = response.json()
    assert len(results.get('results', [])) == 0

def test_empty_query_search(client):
    """Test une recherche avec requête vide"""
    response = client.post(
        "/api/pdf/search",
        json={"query": ""}
    )
    
    assert response.status_code == 400