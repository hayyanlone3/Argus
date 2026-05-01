import asyncio
import json

_subscribers = []

def subscribe():
    q = asyncio.Queue()
    _subscribers.append(q)
    return q

def unsubscribe(q):
    try:
        _subscribers.remove(q)
    except ValueError:
        pass

async def _publish_async(data):
    payload = data
    for q in list(_subscribers):
        try:
            await q.put(payload)
        except Exception:
            try:
                _subscribers.remove(q)
            except Exception:
                pass

def notify_incident(data):
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_publish_async(data))
    except RuntimeError:
        pass
