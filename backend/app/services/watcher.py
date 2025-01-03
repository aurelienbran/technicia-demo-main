import logging
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .indexing import IndexingService

logger = logging.getLogger("technicia.watcher")

class PDFHandler(FileSystemEventHandler):
    def __init__(self, indexing_service):
        self.indexing_service = indexing_service
        self.processing = set()

    def _get_file_hash(self, file_path):
        return self.indexing_service._get_file_hash(file_path)

    async def process_file(self, file_path):
        if file_path in self.processing:
            return

        try:
            self.processing.add(file_path)
            file_hash = self._get_file_hash(file_path)
            logger.info(f"File {file_path} needs indexing with hash {file_hash}")

            logger.info(f"Processing file: {file_path}")
            result = await self.indexing_service.index_document(file_path)

            if result.get("status") == "success":
                logger.info(f"Successfully indexed: {file_path}")
            else:
                logger.error(f"Failed to index {file_path}: {result.get('error', 'Unknown error')}")

        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}")
        finally:
            self.processing.remove(file_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.lower().endswith('.pdf'):
            await self.process_file(event.src_path)

class WatcherService:
    def __init__(self, directory, indexing_service):
        self.directory = directory
        self.handler = PDFHandler(indexing_service)
        self.observer = Observer()

    async def start(self):
        logger.info(f"Started watching directory: {self.directory}")
        self.observer.schedule(self.handler, self.directory, recursive=False)
        self.observer.start()

        # Process existing files
        logger.info("Scanning for existing PDF files...")
        for filename in os.listdir(self.directory):
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(self.directory, filename)
                logger.info(f"Found existing PDF: {file_path}")
                await self.handler.process_file(file_path)

    async def stop(self):
        logger.info("Stopped watching directory")
        self.observer.stop()
        self.observer.join()