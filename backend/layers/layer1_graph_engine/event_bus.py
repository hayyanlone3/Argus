# backend/layers/layer1_graph_engine/event_bus.py
"""
Layer 1: In-memory pub/sub event bus for SSE streaming.
Each subscriber gets its own asyncio.Queue.
Collectors publish node/edge events which are forwarded to connected frontends.
"""

import asyncio
from typing import Any, Dict, Set


class Layer1EventBus:
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=2000)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def publish(self, event: Dict[str, Any]) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # slow consumer; drop event
                pass
            except Exception:
                self.unsubscribe(q)

event_bus = Layer1EventBus()