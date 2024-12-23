import pytest
from pathlib import Path
import os
import base64
from PIL import Image
import io
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
def test_image_to_base64(pdf_service, sample_image):
    """Test la conversion d'image en base64"""
    base64_str = pdf_service._image_to_base64(sample_image)
    assert base64_str.startswith('data:image/png;base64,')
    assert len(base64_str) > 100  # Vérifier qu'il y a des données

def test_create_multimodal_content(pdf_service, sample_image):
    """Test la création du contenu multimodal"""
    content = pdf_service._create_multimodal_content(
        "Test text",
        [sample_image]
    )
    assert len(content) == 2  # texte + image
    assert content[0]['type'] == 'text'
    assert content[1]['type'] == 'image_base64'

# Test du traitement PDF
@pytest.mark.asyncio
async def test_multimodal_embedding(pdf_service):
    """Test la génération d'embedding multimodal"""
    test_text = "Test content"
    embedding = await pdf_service.get_multimodal_embedding(test_text)
    assert len(embedding) == 1024  # Vérifier la dimension du vecteur

@pytest.mark.asyncio
async def test_pdf_with_image_processing(pdf_service, sample_pdf_with_image):
    """Test le traitement d'un PDF contenant une image"""
    result = await pdf_service.process_pdf(sample_pdf_with_image, 'test_with_image.pdf')
    
    assert result is not None
    assert 'chunk_count' in result
    assert result['chunk_count'] > 0
    
    # Vérifier que les métadonnées incluent les infos d'image
    collection_info = pdf_service.vector_store.get_collection_info()
    assert collection_info['vectors_count'] > 0

# Tests du VectorStore
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
    
    # Ajouter les vecteurs
    ids = vector_store.add_vectors(test_vectors, test_metadata)
    assert len(ids) == 1
    
    # Rechercher avec un vecteur similaire
    results = vector_store.search(test_vectors[0], limit=1)
    assert len(results) == 1
    assert results[0]['metadata']['text'] == 'test content'
    assert results[0]['metadata']['has_images'] == True