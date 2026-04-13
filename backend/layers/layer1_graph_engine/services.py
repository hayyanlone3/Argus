# backend/layers/layer1_graph_engine/services.py
"""
Layer 1: Graph Engine Service
Core graph operations: create nodes, edges, query relationships
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.models import Node, Edge, Incident
from database.schemas import NodeCreate, EdgeCreate
from shared.enums import NodeType, EdgeType, Severity
from shared.logger import setup_logger
from config import settings
import networkx as nx
import uuid

logger = setup_logger(__name__)


class GraphService:
    """Layer 1: Provenance Graph Engine Service"""
    
    @staticmethod
    def create_or_update_node(db: Session, node_data: NodeCreate) -> Node:
        """
        Create node or update if exists.
        Prevents duplicates via (type, path, hash) uniqueness.
        
        Args:
            db: Database session
            node_data: NodeCreate schema
            
        Returns:
            Node object (created or updated)
        """
        try:
            # Check if node already exists
            existing_node = db.query(Node).filter(
                Node.type == node_data.type,
                Node.path == node_data.path,
                Node.hash_sha256 == node_data.hash_sha256
            ).first()
            
            if existing_node:
                existing_node.last_seen = datetime.utcnow()
                db.commit()
                logger.debug(f"♻️  Updated node: {node_data.name}")
                return existing_node
            
            # Create new node
            new_node = Node(**node_data.dict())
            new_node.first_seen = datetime.utcnow()
            new_node.last_seen = datetime.utcnow()
            db.add(new_node)
            db.commit()
            db.refresh(new_node)
            
            logger.debug(f"✨ Created node: {node_data.name} (ID: {new_node.id}, Type: {node_data.type})")
            return new_node
        
        except Exception as e:
            logger.error(f"❌ Failed to create/update node: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def create_edge(db: Session, edge_data: EdgeCreate) -> Edge:
        """
        Create edge between two nodes.
        
        Args:
            db: Database session
            edge_data: EdgeCreate schema
            
        Returns:
            Edge object (created)
        """
        try:
            new_edge = Edge(**edge_data.dict())
            new_edge.timestamp = datetime.utcnow()
            db.add(new_edge)
            db.commit()
            db.refresh(new_edge)
            
            logger.debug(f"🔗 Created edge: {edge_data.edge_type} (ID {edge_data.source_id} → {edge_data.target_id})")
            return new_edge
        
        except Exception as e:
            logger.error(f"❌ Failed to create edge: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def get_active_edges(db: Session, hours: int = None) -> list:
        """
        Get edges within active window.
        
        Args:
            db: Database session
            hours: Hours back (default from config)
            
        Returns:
            List of edges
        """
        if hours is None:
            hours = settings.graph_active_window_hours
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        edges = db.query(Edge).filter(Edge.timestamp >= cutoff_time).all()
        logger.debug(f"📊 Found {len(edges)} active edges in last {hours}h")
        return edges
    
    @staticmethod
    def get_node_neighbors(db: Session, node_id: int, hops: int = 2) -> dict:
        """
        Get neighbors of node within N hops.
        Used for graph correlation (Layer 3).
        
        Args:
            db: Database session
            node_id: Node ID
            hops: Maximum hops
            
        Returns:
            {
                "node_id": int,
                "node_name": str,
                "neighbor_count": int,
                "neighbors": [node_ids]
            }
        """
        try:
            node = db.query(Node).filter(Node.id == node_id).first()
            if not node:
                return {"node_id": node_id, "neighbors": []}
            
            # Build graph from edges
            G = nx.DiGraph()
            edges = db.query(Edge).all()
            for edge in edges:
                G.add_edge(edge.source_id, edge.target_id, edge_type=edge.edge_type)
            
            # Get neighbors within N hops
            neighbors = set()
            try:
                if node_id in G:
                    ancestors = nx.ancestors(G, node_id)
                    descendants = nx.descendants(G, node_id)
                    neighbors.update(ancestors)
                    neighbors.update(descendants)
            except:
                pass
            
            logger.debug(f"🗺️  Node {node_id} has {len(neighbors)} neighbors within {hops} hops")
            
            return {
                "node_id": node_id,
                "node_name": node.name,
                "neighbor_count": len(neighbors),
                "neighbors": list(neighbors)
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to get neighbors: {e}")
            return {"node_id": node_id, "neighbors": []}
    
    @staticmethod
    def get_node_path_to_root(db: Session, node_id: int) -> list:
        """
        Get path from node to root (process parent chain).
        
        Args:
            db: Database session
            node_id: Node ID
            
        Returns:
            [node_id, parent_id, grandparent_id, ...]
        """
        try:
            path = [node_id]
            current_id = node_id
            visited = set()
            
            while current_id not in visited:
                visited.add(current_id)
                
                # Find parent via SPAWNED edges
                parent_edge = db.query(Edge).filter(
                    Edge.target_id == current_id,
                    Edge.edge_type == EdgeType.SPAWNED
                ).first()
                
                if not parent_edge:
                    break
                
                current_id = parent_edge.source_id
                path.append(current_id)
            
            logger.debug(f"🌳 Process chain: {' → '.join(str(p) for p in path)}")
            return path
        
        except Exception as e:
            logger.error(f"❌ Failed to get node path: {e}")
            return [node_id]
    
    @staticmethod
    def get_graph_stats(db: Session) -> dict:
        """
        Get graph statistics.
        
        Args:
            db: Database session
            
        Returns:
            {
                "total_nodes": int,
                "total_edges": int,
                "node_breakdown": {...},
                "edge_breakdown": {...},
                "active_edges_24h": int
            }
        """
        try:
            # Count all nodes
            total_nodes = db.query(func.count(Node.id)).scalar()
            
            # Node breakdown by type
            node_breakdown = {}
            for node_type in NodeType:
                count = db.query(func.count(Node.id)).filter(Node.type == node_type).scalar()
                node_breakdown[node_type.value] = count
            
            # Count all edges
            total_edges = db.query(func.count(Edge.id)).scalar()
            
            # Edge breakdown by type
            edge_breakdown = {}
            for edge_type in EdgeType:
                count = db.query(func.count(Edge.id)).filter(Edge.edge_type == edge_type).scalar()
                edge_breakdown[edge_type.value] = count
            
            # Active edges (24h)
            active_edges = len(GraphService.get_active_edges(db))
            
            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "node_breakdown": node_breakdown,
                "edge_breakdown": edge_breakdown,
                "active_edges_24h": active_edges
            }
        
        except Exception as e:
            logger.error(f"❌ Failed to get graph stats: {e}")
            return {}