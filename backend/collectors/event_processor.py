import threading
import queue
from backend.shared.logger import setup_logger

logger = setup_logger(__name__)


class EventProcessor:
    def __init__(self):
        self.event_queue = queue.Queue(maxsize=10000)
        self.running = False
        self.processor_thread = None
    
    def start(self):
        self.running = True
        self.processor_thread = threading.Thread(target=self._process_events, daemon=True)
        self.processor_thread.start()
        logger.info("Event processor started")
    
    def stop(self):
        self.running = False
        if self.processor_thread:
            self.processor_thread.join(timeout=5)
        logger.info("Event processor stopped")
    
    def _process_events(self):
        while self.running:
            try:
                event = self.event_queue.get(timeout=1)
                # Process event through layers
                # (will be implemented in Week 2+)
                logger.debug(f"Processing event: {event}")
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Event processing failed: {e}")
    
    def queue_event(self, event):
        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            logger.warning("Event queue full, dropping event")