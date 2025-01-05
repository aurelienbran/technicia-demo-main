import os
import asyncio
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.services.indexing import IndexingService

logger = logging.getLogger("technicia.watcher")

class FileEventHandler(FileSystemEventHandler):
    def __init__(self, watcher_service):
        self.watcher_service = watcher_service
        self.loop = asyncio.get_event_loop()
        self.processing_files = set()
        super().__init__()

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            if event.src_path not in self.processing_files:
                self.processing_files.add(event.src_path)
                asyncio.run_coroutine_threadsafe(self.watcher_service.on_created(event), self.loop)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            if event.src_path not in self.processing_files:
                self.processing_files.add(event.src_path)
                asyncio.run_coroutine_threadsafe(self.watcher_service.on_modified(event), self.loop)

class WatcherService:
    def __init__(self, watch_path=None, indexing_service=None):
        self.observer = Observer()
        self.watch_path = watch_path
        self.indexing_service = indexing_service
        self.loop = asyncio.get_event_loop()
        self.event_handler = FileEventHandler(self)
        os.makedirs(self.watch_path, exist_ok=True)
        self.observer.schedule(self.event_handler, self.watch_path, recursive=False)

    async def start(self):
        logger.info(f"Starting file watcher on {self.watch_path}")
        self.observer.start()

    async def stop(self):
        logger.info("Stopping file watcher")
        self.observer.stop()
        self.observer.join()

    async def on_created(self, event):
        try:
            await self.process_file(event.src_path)
        finally:
            self.event_handler.processing_files.remove(event.src_path)

    async def on_modified(self, event):
        try:
            await self.process_file(event.src_path)
        finally:
            self.event_handler.processing_files.remove(event.src_path)

    async def process_file(self, file_path):
        try:
            logger.info(f"Processing file: {file_path}")
            await self.indexing_service.index_pdf(file_path)
            logger.info(f"Successfully processed file: {file_path}")
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")