from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio
import logging
import os
from typing import Optional
from queue import Queue
from threading import Thread
from asyncio import AbstractEventLoop

logger = logging.getLogger("technicia.watcher")

class PDFHandler(FileSystemEventHandler):
    def __init__(self, indexing_service, loop: AbstractEventLoop):
        super().__init__()
        self.indexing_service = indexing_service
        self.loop = loop
        self.sync_queue = Queue()
        self._is_processing = False
        self._shutdown = False
        self._processing_thread = None

    def start_processing(self):
        """Démarre le thread de traitement."""
        self._processing_thread = Thread(target=self._process_queue_thread)
        self._processing_thread.daemon = True
        self._processing_thread.start()

    def _process_queue_thread(self):
        """Thread de traitement des fichiers."""
        while not self._shutdown:
            try:
                if not self._is_processing and not self.sync_queue.empty():
                    self._is_processing = True
                    pdf_path = self.sync_queue.get()
                    logger.info(f"Processing file from queue: {pdf_path}")
                    
                    # Utiliser run_coroutine_threadsafe pour appeler index_document
                    future = asyncio.run_coroutine_threadsafe(
                        self.indexing_service.index_document(pdf_path),
                        self.loop
                    )
                    
                    try:
                        result = future.result(timeout=60)  # Timeout de 60 secondes
                        if result["status"] == "success":
                            logger.info(f"Successfully indexed: {pdf_path}")
                        else:
                            logger.error(f"Failed to index {pdf_path}: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        logger.error(f"Error processing {pdf_path}: {str(e)}")
                    finally:
                        self._is_processing = False
                        self.sync_queue.task_done()

            except Exception as e:
                logger.error(f"Error in processing thread: {str(e)}")
                self._is_processing = False
            
            # Petite pause pour éviter de surcharger le CPU
            from time import sleep
            sleep(1)

    def on_created(self, event):
        if event.is_directory or not event.src_path.lower().endswith('.pdf'):
            return
        
        logger.info(f"New PDF detected: {event.src_path}")
        self.sync_queue.put(event.src_path)

    def on_modified(self, event):
        if event.is_directory or not event.src_path.lower().endswith('.pdf'):
            return
        
        logger.info(f"PDF modified: {event.src_path}")
        self.sync_queue.put(event.src_path)

    def stop(self):
        """Arrête le traitement des fichiers."""
        self._shutdown = True
        if self._processing_thread:
            self._processing_thread.join(timeout=5)

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

        # Récupérer la boucle d'événements actuelle
        self.loop = asyncio.get_running_loop()

        # Créer le dossier s'il n'existe pas
        os.makedirs(self.docs_path, exist_ok=True)

        # Configurer le handler et l'observer
        self.handler = PDFHandler(self.indexing_service, self.loop)
        self.observer = Observer()
        self.observer.schedule(self.handler, self.docs_path, recursive=False)
        
        # Démarrer le processus de surveillance
        self.handler.start_processing()
        self.observer.start()
        logger.info(f"Started watching directory: {self.docs_path}")

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
                    # Utiliser la queue synchrone
                    self.handler.sync_queue.put(file_path)
        except Exception as e:
            logger.error(f"Error scanning existing files: {str(e)}")

    async def stop(self) -> None:
        """Arrête la surveillance du dossier."""
        if self.handler:
            self.handler.stop()

        if self.observer is not None:
            self.observer.stop()
            self.observer.join(timeout=2)
            self.observer = None
            logger.info("Stopped watching directory")