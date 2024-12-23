import pytest
from pathlib import Path
import os
import base64
from PIL import Image
import io
import uuid
from backend.services.pdf_service import PDFService
from backend.services.vector_store import VectorStore
from backend.services.claude_service import ClaudeService

@pytest.fixture
def sample_image():
    """Crée une image de test simple"""
    img = Image.new('RGB', (100, 100), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

@pytest.fixture
def sample_pdf_with_image(sample_image):
    """Crée un PDF de test avec une image"""
    import fitz
    
    # Créer un nouveau document PDF
    doc = fitz.open()
    page = doc.new_page()
    
    # Ajouter du texte
    page.insert_text((50, 50), "Test PDF with image")
    
    # Ajouter l'image
    img_rect = fitz.Rect(100, 100, 200, 200)
    page.insert_image(img_rect, stream=sample_image)
    
    # Sauvegarder le PDF
    pdf_path = Path('test_with_image.pdf')
    doc.save(str(pdf_path))
    doc.close()
    
    with open(pdf_path, 'rb') as f:
        content = f.read()
    
    pdf_path.unlink()
    return content

# Fixtures pour les tests
@pytest.fixture
def pdf_service():
    # Utiliser un dossier temporaire pour les tests
    storage_path = 'test_storage/pdfs'
    index_path = 'test_storage/index'
    service = PDFService(storage_path=storage_path, index_path=index_path)
    yield service
    # Nettoyage après les tests
    path = Path(storage_path).parent
    if path.exists():
        import shutil
        shutil.rmtree(path)

@pytest.fixture
def vector_store():
    store = VectorStore()
    yield store
    # Nettoyer la collection après les tests
    store.clear_collection()

@pytest.fixture
def claude_service():
    return ClaudeService()

# Tests des méthodes utilitaires
def test_vector_store_initialization(vector_store):
    """Test l'initialisation du Vector Store"""
    assert vector_store is not None
    info = vector_store.get_collection_info()
    assert 'vectors_count' in info

def test_vector_operations(vector_store):
    """Test les opérations de base sur les vecteurs"""
    # Créer des vecteurs de test
    test_vectors = [[0.1] * 1024]  # dimension pour multimodal-3
    test_metadata = [{
        'text': 'test content',
        'page': 1,
        'has_images': True,
        'image_count': 1
    }]
    
    # Créer un ID UUID valide
    test_ids = [str(uuid.uuid4())]
    
    # Ajouter les vecteurs
    ids = vector_store.add_vectors(test_vectors, test_metadata, test_ids)
    assert len(ids) == 1
    
    # Vérifier que l'ID est celui qu'on a fourni
    assert ids[0] == test_ids[0]
    
    # Rechercher avec un vecteur similaire
    results = vector_store.search(test_vectors[0], limit=1)
    assert len(results) == 1
    assert results[0]['metadata']['text'] == 'test content'
    assert results[0]['id'] == test_ids[0]

@pytest.mark.asyncio
async def test_pdf_with_image_processing(pdf_service, sample_pdf_with_image):
    """Test le traitement d'un PDF contenant une image"""
    try:
        result = await pdf_service.process_pdf(sample_pdf_with_image, 'test_with_image.pdf')
        
        assert result is not None
        assert 'chunk_count' in result
        assert result['chunk_count'] > 0
        
        # Vérifier que les métadonnées incluent les infos d'image
        info = pdf_service.vector_store.get_collection_info()
        assert info['vectors_count'] > 0
        
        # Tester la recherche
        search_results = await pdf_service.search_content("Test PDF")
        assert len(search_results) > 0
        assert search_results[0]['score'] > 0
    finally:
        # Nettoyage explicite
        if hasattr(pdf_service, 'vector_store'):
            pdf_service.vector_store.clear_collection()