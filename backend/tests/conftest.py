import pytest
import os
from pathlib import Path

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configure l'environnement de test"""
    # Créer les dossiers de test
    os.environ["TEST_MODE"] = "true"
    test_storage = Path("test_storage")
    test_storage.mkdir(exist_ok=True)
    
    yield
    
    # Nettoyage après tous les tests
    if test_storage.exists():
        import shutil
        shutil.rmtree(test_storage)

@pytest.fixture
def sample_pdf_content():
    """Fournit un contenu PDF minimal pour les tests"""
    return b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>"

@pytest.fixture
def test_vectors():
    """Fournit des vecteurs de test"""
    return [
        [0.1] * 1024,  # Premier vecteur
        [0.2] * 1024,  # Deuxième vecteur
    ]

@pytest.fixture
def test_metadata():
    """Fournit des métadonnées de test"""
    return [
        {
            "filename": "test1.pdf",
            "page": 1,
            "text": "Contenu de test 1"
        },
        {
            "filename": "test2.pdf",
            "page": 1,
            "text": "Contenu de test 2"
        }
    ]