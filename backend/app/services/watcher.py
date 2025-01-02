from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger("technicia.watcher")

class PDFHandler(FileSystemEventHandler):
    def __init__(self, indexing_service):
        super().__init__()
        self.indexing_service = indexing_service
        self.processing_queue = asyncio.Queue()
        self._is_processing = False
        self._shutdown = False

    async def process_pdf(self, pdf_path: str) -> None:
        """Traite un fichier PDF en utilisant le service d'indexation existant."""
        try:
            await asyncio.sleep(1)  # Attendre que le fichier soit complètement écrit
            logger.info(f"Starting processing of {pdf_path}")
            result = await self.indexing_service.index_document(pdf_path)
            if result["status"] == "success":
                logger.info(f"Successfully indexed: {pdf_path}")
            else:
                logger.error(f"Failed to index {pdf_path}: {result.get('error', 'Unknown error')}")
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {str(e)}")

    async def process_queue(self) -> None:
        """Traite la file d'attente des PDFs."""
        while not self._shutdown:
            if self._is_processing:
                await asyncio.sleep(1)
                continue

            self._is_processing = True
            try:
                while not self.processing_queue.empty():
                    pdf_path = await self.processing_queue.get()
                    await self.process_pdf(pdf_path)
                    self.processing_queue.task_done()
            finally:
                self._is_processing = False
                await asyncio.sleep(1)

    def handle_file(self, file_path: str) -> None:
        """Ajoute un fichier à la queue de traitement."""
        logger.info(f"Adding file to queue: {file_path}")
        asyncio.create_task(self.processing_queue.put(file_path))

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
        self._queue_processor_task = None

    async def start(self) -> None:
        """Démarre la surveillance du dossier docs/."""
        if self.observer is not None:
            logger.warning("Observer already running")
            return

        # Créer le dossier s'il n'existe pas
        os.makedirs(self.docs_path, exist_ok=True)

        # Configurer le handler et l'observer
        self.handler = PDFHandler(self.indexing_service)
        self.observer = Observer()
        self.observer.schedule(self.handler, self.docs_path, recursive=False)
        
        # Démarrer la surveillance
        self.observer.start()
        logger.info(f"Started watching directory: {self.docs_path}")

        # Démarrer le processeur de queue
        self._queue_processor_task = asyncio.create_task(self.handler.process_queue())

        # Indexer les fichiers existants
        await self.index_existing_files()

    async def index_existing_files(self) -> None:
        """Indexe les fichiers PDF existants dans le dossier."""
        logger.info("Scanning for existing PDF files...")
        try:
            for file in os.listdir(self.docs_path):
                if file.lower().endswith('.pdf'):
                    file_path = os.path.join(self.docs_path, file)
                    logger.info(f"Found existing PDF: {file_path}")
                    self.handler.handle_file(file_path)
        except Exception as e:
            logger.error(f"Error scanning existing files: {str(e)}")

    async def stop(self) -> None:
        """Arrête la surveillance du dossier."""
        if self.handler:
            self.handler._shutdown = True

        if self._queue_processor_task:
            try:
                self._queue_processor_task.cancel()
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass

        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=2)
            self.observer = None
            logger.info("Stopped watching directory")
