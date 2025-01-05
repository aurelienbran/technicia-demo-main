import os
import asyncio
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.services.indexing import IndexingService

class FileEventHandler(FileSystemEventHandler):
    def __init__(self, watcher_service):
        self.watcher_service = watcher_service
        super().__init__()

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            asyncio.create_task(self.watcher_service.on_created(event))

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.pdf'):
            asyncio.create_task(self.watcher_service.on_modified(event))

class WatcherService:
    def __init__(self):
        self.observer = Observer()
        self.event_handler = FileEventHandler(self)
        self.indexing_service = IndexingService()
        self.watch_path = os.path.join(os.path.dirname(__file__), '..', '..', 'docs')
        os.makedirs(self.watch_path, exist_ok=True)
        self.observer.schedule(self.event_handler, self.watch_path, recursive=False)

    def start(self):
        logging.info(f"Starting file watcher on {self.watch_path}")
        self.observer.start()

    def stop(self):
        logging.info("Stopping file watcher")
        self.observer.stop()
        self.observer.join()

    async def process_file(self, file_path):
        try:
            logging.info(f"Processing file: {file_path}")
            await self.indexing_service.index_pdf(file_path)
            logging.info(f"Successfully processed file: {file_path}")
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {str(e)}")

    async def on_created(self, event):
        await self.process_file(event.src_path)

    async def on_modified(self, event):
        await self.process_file(event.src_path)
