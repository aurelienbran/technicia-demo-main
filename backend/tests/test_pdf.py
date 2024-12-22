import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from main import app

client = TestClient(app)

def test_pdf_upload():
    # Créer un PDF de test
    pdf_path = Path('tests/data/test.pdf')
    
    with open(pdf_path, 'rb') as f:
        response = client.post(
            '/api/pdf/upload',
            files={'file': ('test.pdf', f, 'application/pdf')}
        )
    
    assert response.status_code == 200
    assert 'filename' in response.json()
    assert 'content' in response.json()

def test_list_files():
    response = client.get('/api/pdf/files')
    assert response.status_code == 200
    assert isinstance(response.json(), list)
