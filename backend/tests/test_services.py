import pytest
from pathlib import Path
import os
from services.pdf_service import PDFService
from services.vector_store import VectorStore
from services.claude_service import ClaudeService

# Fixtures pour les tests
@pytest.fixture
def pdf_service():
    # Utiliser un dossier temporaire pour les tests
    storage_path = 'test_storage/pdfs'
    index_path = 'test_storage/index'
    service = PDFService(storage_path=storage_path, index_path=index_path)
    yield service
    # Nettoyage après les tests
    if Path(storage_path).exists():
        Path(storage_path).unlink()
    if Path(index_path).exists():
        Path(index_path).unlink()

@pytest.fixture
def vector_store():
    store = VectorStore()
    yield store
    # Nettoyer la collection après les tests
    store.clear_collection()

@pytest.fixture
def claude_service():
    return ClaudeService()

# Tests du PDFService
def test_pdf_service_initialization(pdf_service):
    """Test l'initialisation du service PDF"""
    assert pdf_service is not None
    assert Path(pdf_service.storage_path).exists()
    assert Path(pdf_service.index_path).exists()

@pytest.mark.asyncio
async def test_pdf_processing(pdf_service):
    """Test le traitement d'un PDF"""
    # Créer un PDF de test simple
    test_pdf_path = 'test.pdf'
    with open(test_pdf_path, 'wb') as f:
        # TODO: Créer un PDF de test minimal
        pass
    
    with open(test_pdf_path, 'rb') as f:
        content = f.read()
        result = await pdf_service.process_pdf(content, 'test.pdf')
    
    assert result is not None
    assert 'filename' in result
    assert result['filename'] == 'test.pdf'

# Tests du VectorStore
def test_vector_store_initialization(vector_store):
    """Test l'initialisation du Vector Store"""
    assert vector_store is not None
    info = vector_store.get_collection_info()
    assert 'vectors_count' in info

def test_vector_operations(vector_store):
    """Test les opérations de base sur les vecteurs"""
    # Ajouter des vecteurs de test
    test_vectors = [[0.1, 0.2, 0.3] * 341]  # Pour obtenir dim 1024
    test_metadata = [{'text': 'test content', 'page': 1}]
    
    ids = vector_store.add_vectors(test_vectors, test_metadata)
    assert len(ids) == 1
    
    # Rechercher avec un vecteur similaire
    results = vector_store.search(test_vectors[0], limit=1)
    assert len(results) == 1
    assert results[0]['metadata']['text'] == 'test content'

# Tests du ClaudeService
@pytest.mark.asyncio
async def test_claude_response_generation(claude_service):
    """Test la génération de réponses"""
    test_query = "Que fait ce système ?"
    test_context = [
        {
            'filename': 'test.pdf',
            'page_num': 1,
            'text': 'Ce système est un assistant technique.',
            'score': 0.95
        }
    ]
    
    response = await claude_service.generate_response(test_query, test_context)
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0

@pytest.mark.asyncio
async def test_document_summarization(claude_service):
    """Test la génération de résumés"""
    test_chunks = [
        {
            'filename': 'test.pdf',
            'page_num': 1,
            'text': 'Document de test avec du contenu technique.',
            'score': 1.0
        }
    ]
    
    summary = await claude_service.generate_summary(test_chunks)
    assert summary is not None
    assert isinstance(summary, str)
    assert len(summary) > 0