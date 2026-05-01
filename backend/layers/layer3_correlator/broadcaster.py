import asyncio
import json
import threading
from backend.shared.logger import setup_logger

logger = setup_logger(__name__)

_subscribers = []
_main_loop = None  # Will be set by uvicorn's main thread

async def subscribe():
    q = asyncio.Queue()
    _subscribers.append(q)
    logger.warning(f"📡 SSE: New subscriber connected (total: {len(_subscribers)})")
    return q

def unsubscribe(q):
    try:
        _subscribers.remove(q)
        logger.warning(f"📡 SSE: Subscriber disconnected (total: {len(_subscribers)})")
    except ValueError:
        pass

async def _publish_async(data):
    """Broadcast to all subscribers - runs on main event loop"""
    payload = data
    count = 0
    failed = 0
    for q in list(_subscribers):
        try:
            await q.put(payload)
            count += 1
        except Exception as e:
            logger.debug(f"📡 SSE: Failed to send to queue: {e}")
            failed += 1
            try:
                _subscribers.remove(q)
            except Exception:
                pass
    logger.warning(f"📡 SSE: Broadcast sent to {count} subscribers (failed: {failed})")

def set_event_loop(loop):
    """Called by main.py to register the uvicorn event loop"""
    global _main_loop
    _main_loop = loop
    logger.warning(f"📡 SSE: Main event loop registered")

def notify_incident(data):
    """Called from worker threads to broadcast incidents"""
    try:
        session_id = data.get('session_id', 'unknown')
        logger.warning(f"📡 SSE: notify_incident called from thread '{threading.current_thread().name}' with session_id={session_id}")
        
        if _main_loop is None:
            logger.error(f"📡 SSE: Main event loop not set!")
            return
        
        # Use thread-safe call to schedule on main loop
        future = asyncio.run_coroutine_threadsafe(_publish_async(data), _main_loop)
        logger.warning(f"📡 SSE: Scheduled broadcast on main loop")
        
    except Exception as e:
        logger.error(f"📡 SSE: notify_incident error: {e}", exc_info=True)
