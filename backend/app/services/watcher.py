from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger("technicia.watcher")

class PDFHandler(FileSystemEventHandler):
    def __init__(self, indexing_service, loop=None):
        self.indexing_service = indexing_service
        self.processing_queue = asyncio.Queue()
        self._is_processing = False
        self.loop = loop or asyncio.get_event_loop()

    async def process_pdf(self, pdf_path: str) -> None:
        """Traite un fichier PDF en utilisant le service d'indexation existant."""
        try:
            result = await self.indexing_service.index_document(pdf_path)
            if result["status"] == "success":
                logger.info(f"Successfully indexed: {pdf_path}")
            else:
                logger.error(f"Failed to index {pdf_path}: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {str(e)}")

    async def process_queue(self) -> None:
        """Traite la file d'attente des PDFs."""
        if self._is_processing:
            return

        self._is_processing = True
        try:
            while not self.processing_queue.empty():
                pdf_path = await self.processing_queue.get()
                await self.process_pdf(pdf_path)
                self.processing_queue.task_done()
        finally:
            self._is_processing = False

    def handle_file(self, file_path: str) -> None:
        """Méthode synchrone pour gérer l'ajout de fichiers à la queue."""
        asyncio.run_coroutine_threadsafe(
            self.processing_queue.put(file_path), 
            self.loop
        )
        asyncio.run_coroutine_threadsafe(
            self.process_queue(), 
            self.loop
        )

    def on_created(self, event):
        if event.is_directory or not event.src_path.lower().endswith('.pdf'):
            return
        
        logger.info(f"New PDF detected: {event.src_path}")
        self.handle_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory or not event.src_path.lower().endswith('.pdf'):
            return
        
        logger.info(f"PDF modified: {event.src_path}")
        self.handle_file(event.src_path)

class WatcherService:
    def __init__(self, docs_path: str, indexing_service):
        self.docs_path = docs_path
        self.indexing_service = indexing_service
        self.observer: Optional[Observer] = None
        self.handler: Optional[PDFHandler] = None
        self.loop = None

    async def start(self) -> None:
        """Démarre la surveillance du dossier docs/."""
        if self.observer is not None:
            logger.warning("Observer already running")
            return

        self.loop = asyncio.get_running_loop()
        
        # Créer le handler et l'observer
        self.handler = PDFHandler(self.indexing_service, self.loop)
        self.observer = Observer()
        self.observer.schedule(self.handler, self.docs_path, recursive=False)
        
        # Démarrer la surveillance
        self.observer.start()
        logger.info(f"Started watching directory: {self.docs_path}")

        # Indexer les fichiers existants
        await self.index_existing_files()

    async def index_existing_files(self) -> None:
        """Indexe les fichiers PDF existants dans le dossier."""
        logger.info("Scanning for existing PDF files...")
        for file in os.listdir(self.docs_path):
            if file.lower().endswith('.pdf'):
                file_path = os.path.join(self.docs_path, file)
                await self.handler.processing_queue.put(file_path)
        
        if not self.handler.processing_queue.empty():
            await self.handler.process_queue()

    async def stop(self) -> None:
        """Arrête la surveillance du dossier."""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Stopped watching directory")