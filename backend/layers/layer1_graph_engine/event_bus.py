# # backend/layers/layer1_graph_engine/services.py
# import asyncio
# from typing import Any, Dict, Set
# from sqlalchemy.orm import Session
# from datetime import datetime

# from database.models import Node, Edge
# from database.schemas import NodeCreate, EdgeCreate
# from shared.logger import setup_logger

# logger = setup_logger(__name__)

# class Layer1EventBus:
#     """
#     Simple in-memory pub/sub for SSE.
#     - Each subscriber gets its own queue.
#     - Collectors publish node/edge events.
#     """
#     def __init__(self) -> None:
#         self._subscribers: Set[asyncio.Queue] = set()

#     def subscribe(self) -> asyncio.Queue:
#         q: asyncio.Queue = asyncio.Queue(maxsize=2000)
#         self._subscribers.add(q)
#         return q

#     def unsubscribe(self, q: asyncio.Queue) -> None:
#         self._subscribers.discard(q)

#     async def publish(self, event: Dict[str, Any]) -> None:
#         dead = []
#         for q in list(self._subscribers):
#             try:
#                 q.put_nowait(event)
#             except asyncio.QueueFull:
#                 # drop if client is too slow
#                 pass
#             except Exception:
#                 dead.append(q)
#         for q in dead:
#             self.unsubscribe(q)

# # Global singleton for the event bus
# event_bus = Layer1EventBus()


# class GraphService:
#     @staticmethod
#     def create_or_update_node(db: Session, node_data: NodeCreate) -> Node:
#         """Create a new node or update an existing one based on hash or path."""
#         existing_node = None
        
#         if node_data.hash_sha256:
#             existing_node = db.query(Node).filter(Node.hash_sha256 == node_data.hash_sha256).first()
#         elif node_data.path:
#             existing_node = db.query(Node).filter(Node.path == node_data.path).first()

#         if existing_node:
#             existing_node.last_seen = datetime.utcnow()
#             # Update optional fields if provided
#             if node_data.path_risk is not None:
#                 existing_node.path_risk = node_data.path_risk
#         else:
#             existing_node = Node(
#                 type=node_data.type,
#                 name=node_data.name,
#                 path=node_data.path,
#                 hash_sha256=node_data.hash_sha256,
#                 path_risk=node_data.path_risk
#             )
#             db.add(existing_node)

#         db.commit()
#         db.refresh(existing_node)

#         # Publish node update to SSE
#         try:
#             awaitable = event_bus.publish({
#                 "type": "node_updated",
#                 "node": {
#                     "id": existing_node.id,
#                     "type": existing_node.type.value if hasattr(existing_node.type, 'value') else existing_node.type,
#                     "name": existing_node.name,
#                     "path": existing_node.path,
#                     "hash_sha256": existing_node.hash_sha256,
#                     "path_risk": existing_node.path_risk,
#                     "first_seen": existing_node.first_seen.isoformat() if existing_node.first_seen else None,
#                     "last_seen": existing_node.last_seen.isoformat() if existing_node.last_seen else None,
#                 },
#             })
#             # publish is async; schedule it without blocking request thread
#             try:
#                 loop = asyncio.get_running_loop()
#                 loop.create_task(awaitable)
#             except RuntimeError:
#                 # Fallback if called from a pure sync thread without a running loop
#                 asyncio.run(awaitable)
#         except Exception as e:
#             logger.warning(f"Failed to publish node_updated event: {e}")

#         return existing_node

#     @staticmethod
#     def create_edge(db: Session, edge_data: EdgeCreate) -> Edge:
#         """Create a new edge in the graph."""
#         edge = Edge(
#             source_id=edge_data.source_id,
#             target_id=edge_data.target_id,
#             edge_type=edge_data.edge_type,
#             session_id=edge_data.session_id,
#             timestamp=datetime.utcnow()
#         )
        
#         db.add(edge)
#         db.commit()
#         db.refresh(edge)

#         # Publish edge creation to SSE
#         try:
#             awaitable = event_bus.publish({
#                 "type": "edge_created",
#                 "edge": {
#                     "id": edge.id,
#                     "source_id": edge.source_id,
#                     "target_id": edge.target_id,
#                     "edge_type": edge.edge_type.value if hasattr(edge.edge_type, 'value') else edge.edge_type,
#                     "timestamp": edge.timestamp.isoformat() if edge.timestamp else None,
#                     "session_id": edge.session_id
#                 },
#             })
#             # publish is async; schedule it without blocking request thread
#             try:
#                 loop = asyncio.get_running_loop()
#                 loop.create_task(awaitable)
#             except RuntimeError:
#                 asyncio.run(awaitable)
#         except Exception as e:
#             logger.warning(f"Failed to publish edge_created event: {e}")

#         return edge

#     @staticmethod
#     def get_node_neighbors(db: Session, node_id: int, hops: int = 2) -> Dict[str, Any]:
#         """Fetch node neighbors within N hops."""
#         # Note: Implement graph traversal logic here
#         visited = set()
#         queue = [(node_id, 0)]
        
#         while queue:
#             current_id, current_hop = queue.pop(0)
#             if current_hop >= hops:
#                 continue
                
#             visited.add(current_id)
            
#             # Find all outgoing and incoming edges for current_id
#             edges = db.query(Edge).filter((Edge.source_id == current_id) | (Edge.target_id == current_id)).all()
            
#             for e in edges:
#                 neighbor = e.target_id if e.source_id == current_id else e.source_id
#                 if neighbor not in visited:
#                     queue.append((neighbor, current_hop + 1))
                    
#         return {
#             "seed": node_id,
#             "hops": hops,
#             "neighbors": list(visited - {node_id})
#         }

#     @staticmethod
#     def get_node_path_to_root(db: Session, node_id: int) -> list:
#         """Trace spawned edges backwards to root."""
#         path = [node_id]
#         current_id = node_id
        
#         while True:
#             parent_edge = db.query(Edge).filter(
#                 Edge.target_id == current_id, 
#                 Edge.edge_type == "SPAWNED"
#             ).first()
            
#             if not parent_edge or parent_edge.source_id in path:
#                 break
                
#             current_id = parent_edge.source_id
#             path.append(current_id)
            
#         return path

#     @staticmethod
#     def get_graph_stats(db: Session) -> Dict[str, Any]:
#         return {
#             "total_nodes": db.query(Node).count(),
#             "total_edges": db.query(Edge).count()
#         }

#     @staticmethod
#     def get_active_edges(db: Session, hours: int = 24):
#         # Simplified for returning recent edges
#         from datetime import timedelta
#         cutoff = datetime.utcnow() - timedelta(hours=hours)
#         return db.query(Edge).filter(Edge.timestamp >= cutoff).all()




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