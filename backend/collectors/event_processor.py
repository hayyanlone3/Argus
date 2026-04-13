import threading
import queue
from shared.logger import setup_logger

logger = setup_logger(__name__)


class EventProcessor:
    """
    Main event processing loop.
    Collects ETW events and routes to Layers 0-3.
    """
    
    def __init__(self):
        self.event_queue = queue.Queue(maxsize=10000)
        self.running = False
        self.processor_thread = None
    
    def start(self):
        """Start event processor in background thread."""
        self.running = True
        self.processor_thread = threading.Thread(target=self._process_events, daemon=True)
        self.processor_thread.start()
        logger.info("🚀 Event processor started")
    
    def stop(self):
        """Stop event processor."""
        self.running = False
        if self.processor_thread:
            self.processor_thread.join(timeout=5)
        logger.info("🛑 Event processor stopped")
    
    def _process_events(self):
        """Main event loop."""
        while self.running:
            try:
                event = self.event_queue.get(timeout=1)
                # Process event through layers
                # (will be implemented in Week 2+)
                logger.debug(f"Processing event: {event}")
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"❌ Event processing failed: {e}")
    
    def queue_event(self, event):
        """Queue event for processing."""
        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            logger.warning("⚠️  Event queue full, dropping event")