"""
Document AI service for processing PDFs with OCR capabilities.
"""
from typing import Optional, Dict, Any
import os
from google.cloud import documentai
from google.api_core import operations_v1
from google.cloud.documentai_v1 import Document
import logging

logger = logging.getLogger(__name__)

class DocumentAIService:
    """Service to handle Google Cloud Document AI OCR operations."""
    
    def __init__(
        self,
        project_id: str,
        location: str,
        processor_id: str,
        timeout: int = 300
    ):
        """
        Initialize the Document AI service.
        
        Args:
            project_id (str): Google Cloud project ID
            location (str): Location of the processor (e.g., "us", "eu")
            processor_id (str): ID of the Document OCR processor
            timeout (int, optional): Timeout in seconds for API calls. Defaults to 300.
        """
        try:
            # Initialize the Document AI client
            self.client = documentai.DocumentProcessorServiceClient()
            
            # Set up the processor path
            self.processor_name = self.client.processor_path(
                project_id, location, processor_id
            )
            
            self.timeout = timeout
            logger.info(f"DocumentAI service initialized with processor: {self.processor_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize DocumentAI service: {str(e)}")
            raise

    async def process_document(
        self,
        content: bytes,
        mime_type: str = "application/pdf"
    ) -> Optional[Document]:
        """
        Process a single document using Document AI OCR.
        
        Args:
            content (bytes): The document content in bytes
            mime_type (str, optional): MIME type of the document. Defaults to "application/pdf".
            
        Returns:
            Optional[Document]: Processed document if successful, None otherwise
        """
        try:
            # Prepare the request
            raw_document = documentai.RawDocument(
                content=content,
                mime_type=mime_type
            )
            
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )
            
            logger.info("Sending document for OCR processing...")
            
            # Process the document
            result = await self.client.process_document(request)
            
            if result.document:
                logger.info("Document processed successfully")
                return result.document
            else:
                logger.warning("No document returned from processing")
                return None
                
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise

    def extract_text_and_layout(self, document: Document) -> Dict[str, Any]:
        """
        Extract text and layout information from a processed document.
        
        Args:
            document (Document): The processed Document AI document
            
        Returns:
            Dict[str, Any]: Dictionary containing extracted text and layout information
        """
        try:
            # Extract basic text
            extracted_data = {
                'text': document.text,
                'pages': []
            }
            
            # Process each page
            for page in document.pages:
                page_data = {
                    'page_number': page.page_number,
                    'dimensions': {
                        'width': page.dimension.width,
                        'height': page.dimension.height
                    },
                    'paragraphs': [],
                    'blocks': [],
                    'detected_languages': []
                }
                
                # Extract paragraphs
                for paragraph in page.paragraphs:
                    page_data['paragraphs'].append({
                        'text': paragraph.text,
                        'confidence': paragraph.confidence,
                        'bounding_box': [
                            {
                                'x': vertex.x,
                                'y': vertex.y
                            }
                            for vertex in paragraph.layout.bounding_poly.vertices
                        ]
                    })
                
                # Extract text blocks
                for block in page.blocks:
                    page_data['blocks'].append({
                        'text': block.text,
                        'confidence': block.confidence
                    })
                
                # Extract detected languages
                for language in page.detected_languages:
                    page_data['detected_languages'].append({
                        'language_code': language.language_code,
                        'confidence': language.confidence
                    })
                
                extracted_data['pages'].append(page_data)
            
            logger.info(f"Successfully extracted text and layout from document")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting text and layout: {str(e)}")
            raise

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.close()
