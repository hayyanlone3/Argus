# backend/layers/layer1_graph_engine/routes.py
"""
Layer 1: Graph Engine API Endpoints
Provides node and edge management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Node, Edge
from database.schemas import (
    NodeCreate, EdgeCreate, NodeResponse, EdgeResponse
)
from .services import GraphService
from shared.logger import setup_logger
import json
import asyncio

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    """Layer 1: Graph Engine health check."""
    return {
        "layer": 1,
        "name": "Graph Engine",
        "status": "operational",
        "features": [
            "Node creation (process, file, script, WMI, registry)",
            "Edge creation (8 types)",
            "Graph traversal (neighbors, paths)",
            "24h active window + 30-day archive",
            "Real-time SSE streaming"
        ]
    }


@router.post("/nodes")
async def create_node(
    node_data: NodeCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new node in graph.
    
    Example:
        POST /api/layer1/nodes
        {
            "type": "process",
            "name": "explorer.exe",
            "path": "C:\\Windows\\explorer.exe",
            "hash_sha256": "abc123...",
            "path_risk": 0.0
        }
    """
    try:
        node = GraphService.create_or_update_node(db, node_data)
        return NodeResponse.from_orm(node)
    except Exception as e:
        logger.error(f"❌ Failed to create node: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes")
async def list_nodes(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    node_type: str = Query(None)
):
    """
    List all nodes (optionally filtered by type).
    
    Example:
        GET /api/layer1/nodes?limit=50&node_type=process
    """
    try:
        query = db.query(Node)
        
        if node_type:
            query = query.filter(Node.type == node_type)
        
        nodes = query.limit(limit).all()
        return {
            "total": len(nodes),
            "nodes": [NodeResponse.from_orm(n) for n in nodes]
        }
    except Exception as e:
        logger.error(f"❌ Failed to list nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: int,
    db: Session = Depends(get_db)
):
    """
    Get single node by ID.
    
    Example:
        GET /api/layer1/nodes/1
    """
    try:
        node = db.query(Node).filter(Node.id == node_id).first()
        
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        
        return NodeResponse.from_orm(node)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get node: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/edges")
async def create_edge(
    edge_data: EdgeCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new edge in graph.
    
    Example:
        POST /api/layer1/edges
        {
            "source_id": 1,
            "target_id": 2,
            "edge_type": "SPAWNED",
            "session_id": "test-001"
        }
    """
    try:
        # Verify nodes exist
        source = db.query(Node).filter(Node.id == edge_data.source_id).first()
        target = db.query(Node).filter(Node.id == edge_data.target_id).first()
        
        if not source or not target:
            raise HTTPException(status_code=404, detail="Source or target node not found")
        
        edge = GraphService.create_edge(db, edge_data)
        return EdgeResponse.from_orm(edge)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create edge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edges")
async def list_edges(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    edge_type: str = Query(None),
    session_id: str = Query(None)
):
    """
    List all edges (optionally filtered).
    
    Example:
        GET /api/layer1/edges?limit=50&edge_type=SPAWNED
    """
    try:
        query = db.query(Edge)
        
        if edge_type:
            query = query.filter(Edge.edge_type == edge_type)
        
        if session_id:
            query = query.filter(Edge.session_id == session_id)
        
        edges = query.order_by(Edge.timestamp.desc()).limit(limit).all()
        return {
            "total": len(edges),
            "edges": [EdgeResponse.from_orm(e) for e in edges]
        }
    except Exception as e:
        logger.error(f"❌ Failed to list edges: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/edges/{edge_id}")
async def get_edge(
    edge_id: int,
    db: Session = Depends(get_db)
):
    """
    Get single edge by ID.
    
    Example:
        GET /api/layer1/edges/1
    """
    try:
        edge = db.query(Edge).filter(Edge.id == edge_id).first()
        
        if not edge:
            raise HTTPException(status_code=404, detail="Edge not found")
        
        return EdgeResponse.from_orm(edge)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get edge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neighbors/{node_id}")
async def get_neighbors(
    node_id: int,
    hops: int = Query(2, ge=1, le=5),
    db: Session = Depends(get_db)
):
    """
    Get node neighbors within N hops (for correlation).
    
    Example:
        GET /api/layer1/neighbors/1?hops=2
    """
    try:
        result = GraphService.get_node_neighbors(db, node_id, hops)
        return result
    except Exception as e:
        logger.error(f"❌ Failed to get neighbors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/path-to-root/{node_id}")
async def get_path_to_root(
    node_id: int,
    db: Session = Depends(get_db)
):
    """
    Get process parent chain (path to root).
    
    Example:
        GET /api/layer1/path-to-root/5
    """
    try:
        path = GraphService.get_node_path_to_root(db, node_id)
        
        # Get node details for each ID in path
        nodes = []
        for nid in path:
            node = db.query(Node).filter(Node.id == nid).first()
            if node:
                nodes.append({
                    "id": node.id,
                    "name": node.name,
                    "type": node.type.value,
                    "path": node.path
                })
        
        return {
            "root_chain": path,
            "nodes": nodes,
            "chain_length": len(path)
        }
    except Exception as e:
        logger.error(f"❌ Failed to get path to root: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_graph_stats(db: Session = Depends(get_db)):
    """
    Get graph statistics.
    
    Example:
        GET /api/layer1/stats
    """
    try:
        stats = GraphService.get_graph_stats(db)
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream")
async def stream_graph_updates(db: Session = Depends(get_db)):
    """
    Server-Sent Events stream of graph updates.
    Frontend connects here for real-time graph changes.
    
    Example:
        GET /api/layer1/stream
    """
    async def event_generator():
        try:
            for i in range(60):  # Stream for 60 seconds
                edges = GraphService.get_active_edges(db, hours=24)
                nodes = db.query(Node).count()
                
                yield f"data: {json.dumps({'nodes': nodes, 'edges': len(edges), 'timestamp': str(__import__('datetime').datetime.utcnow())})}\n\n"
                
                await asyncio.sleep(5)  # Send update every 5 seconds
        
        except Exception as e:
            logger.error(f"❌ Stream error: {e}")
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")