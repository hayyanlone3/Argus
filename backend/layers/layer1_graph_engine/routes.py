# backend/layers/layer1_graph_engine/routes.py
"""
Layer 1: Graph Engine API Endpoints
Provides node and edge management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Node, Edge
from database.schemas import (
    NodeCreate, EdgeCreate, NodeResponse, EdgeResponse
)
from .services import GraphService
from layers.layer1_graph_engine.event_bus import event_bus
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
        
        nodes = query.order_by(Node.last_seen.desc()).limit(limit).all()
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


@router.get("/edges/interesting")
async def list_interesting_edges(
    db: Session = Depends(get_db),
    limit: int = Query(250, ge=1, le=2000),
    min_anomaly_score: float = Query(0.6, ge=0.0, le=1.0),
    min_severity: str = Query("UNKNOWN"),
):
    """
    Return only edges that are likely suspicious (used for incident-centric graph view).
    """
    try:
        # Map severities to rank
        rank = {"BENIGN": 0, "UNKNOWN": 1, "WARNING": 2, "CRITICAL": 3}
        min_rank = rank.get(min_severity.upper(), 1)

        edges = (
            db.query(Edge)
            .order_by(Edge.timestamp.desc())
            .limit(limit)
            .all()
        )

        # Filter in python to avoid enum/db quirks; can be optimized later
        def sev_rank(e):
            s = getattr(e.final_severity, "value", e.final_severity) or "BENIGN"
            return rank.get(str(s).upper(), 0)

        interesting = [
            e for e in edges
            if (e.anomaly_score is not None and float(e.anomaly_score) >= float(min_anomaly_score))
            or sev_rank(e) >= min_rank
        ]

        return {
            "total": len(interesting),
            "edges": [EdgeResponse.from_orm(e) for e in interesting],
        }
    except Exception as e:
        logger.error(f"❌ Failed to list interesting edges: {e}")
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


@router.get("/subgraph")
async def get_subgraph(
    seed_node_id: int = Query(..., ge=1),
    hops: int = Query(2, ge=1, le=5),
    limit_edges: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    """
    Return a subgraph centered on seed_node_id.

    Example:
      GET /api/layer1/subgraph?seed_node_id=123&hops=2&limit_edges=1000

    Returns:
      { "seed_node_id": 123, "hops": 2, "nodes": [...], "edges": [...], "counts": {...} }
    """
    try:
        neigh = GraphService.get_node_neighbors(db, seed_node_id, hops)
        node_ids = set(neigh.get("neighbors", []))
        node_ids.add(seed_node_id)

        nodes = db.query(Node).filter(Node.id.in_(node_ids)).all()

        edges_q = db.query(Edge).filter(
            Edge.source_id.in_(node_ids),
            Edge.target_id.in_(node_ids),
        ).order_by(Edge.timestamp.desc()).limit(limit_edges)

        edges = edges_q.all()

        return {
            "seed_node_id": seed_node_id,
            "hops": hops,
            "counts": {"nodes": len(nodes), "edges": len(edges)},
            "nodes": [NodeResponse.from_orm(n) for n in nodes],
            "edges": [EdgeResponse.from_orm(e) for e in edges],
        }

    except Exception as e:
        logger.error(f"❌ Failed to get subgraph: {e}")
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
async def stream_graph_updates(
    request: Request,
    suspicious_only: bool = Query(True),
    sysmon_only: bool = Query(True),
    min_anomaly_score: float = Query(0.6, ge=0.0, le=1.0),
):
    """
    SSE stream of real Layer1 edge events.
    Defaults:
      - suspicious_only=true
      - sysmon_only=true
    """
    q = event_bus.subscribe()

    def is_suspicious(edge: dict) -> bool:
        sev = (edge.get("final_severity") or "").upper()
        score = edge.get("anomaly_score") or 0.0
        # treat UNKNOWN/WARNING/CRITICAL as interesting
        return (sev in {"UNKNOWN", "WARNING", "CRITICAL"}) or (float(score) >= float(min_anomaly_score))

    def is_sysmon(edge: dict) -> bool:
        md = edge.get("edge_metadata") or {}
        return md.get("collector") == "sysmon"

    async def gen():
        try:
            yield f"data: {json.dumps({'type':'hello','suspicious_only':suspicious_only,'sysmon_only':sysmon_only})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=15.0)

                    if evt.get("type") == "edge_created":
                        edge = evt.get("edge") or {}
                        if sysmon_only and not is_sysmon(edge):
                            continue
                        if suspicious_only and not is_suspicious(edge):
                            continue

                    yield f"data: {json.dumps(evt)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type':'ping'})}\n\n"
        finally:
            event_bus.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream")