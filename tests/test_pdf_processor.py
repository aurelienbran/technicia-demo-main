import pytest
from backend.services.pdf_processor import PDFProcessor

@pytest.fixture
def pdf_processor():
    return PDFProcessor()

def test_extract_text(pdf_processor):
    result = pdf_processor.extract_text('tests/data/sample.pdf')
    assert len(result) > 0
    assert isinstance(result[0], str)

@pytest.mark.asyncio
async def test_process_pdf(pdf_processor):
    result = await pdf_processor.process_pdf('tests/data/sample.pdf')
    assert len(result) > 0
    assert 'text' in result[0]
    assert 'embedding' in result[0]