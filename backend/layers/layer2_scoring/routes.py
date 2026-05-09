from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from backend.database.connection import get_db
from backend.database.models import Edge, Node
from backend.shared.logger import setup_logger
from .scoring import ScoringEngine
from .voting_logic import VotingEngine

from backend.layers.layer2_scoring.runtime_engine import LATEST_DECISIONS, LATEST_LOCK
from backend.layers.layer2_scoring import event_stream
from backend.layers.layer2_scoring.event_stream import TelemetryEvent, publish_event
import os

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    return {
        "layer": 2,
        "name": "Scoring Engine",
        "status": "operational",
        "channels": [
            "2A: Math Certainty (entropy, spawn rate, rename burst)",
            "2B: Statistical Impossibility (P-matrix baseline)",
            "2C: ML Graph Anomaly (River HalfSpaceTrees)"
        ],
        "output": "BENIGN | UNKNOWN | WARNING | CRITICAL"
    }


@router.get("/live/ping")
async def live_ping():
    return {"ok": True}


@router.post("/score-channel-2a")
async def score_channel_2a(
    process_node_id: int,
    db: Session = Depends(get_db)
):
    try:
        # Verify node exists
        node = db.query(Node).filter(Node.id == process_node_id).first()
        if not node:
            raise HTTPException(status_code=404, detail="Process node not found")
        
        # Calculate signals
        spawn_anomaly, spawn_score, spawn_details = ScoringEngine.calculate_spawn_rate_anomaly(db, process_node_id)
        rename_anomaly, rename_score, rename_details = ScoringEngine.calculate_rename_burst(db, process_node_id)
        edge_anomaly, edge_score, edge_details = ScoringEngine.calculate_edge_burst(db, process_node_id)
        
        # Final 2A score
        score_2a = ScoringEngine.score_channel_2a(db, process_node_id)
        
        return {
            "channel": "2A",
            "process_node_id": process_node_id,
            "process_name": node.name,
            "score": round(score_2a, 3),
            "signals": {
                "spawn_rate": {
                    "anomalous": spawn_anomaly,
                    "score": round(spawn_score, 3),
                    "details": spawn_details
                },
                "rename_burst": {
                    "anomalous": rename_anomaly,
                    "score": round(rename_score, 3),
                    "details": rename_details
                },
                "edge_burst": {
                    "anomalous": edge_anomaly,
                    "score": round(edge_score, 3),
                    "details": edge_details
                }
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  Failed to score channel 2A: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/score-channel-2b")
async def score_channel_2b(
    edge_entropy: float = Query(0.0, ge=0, le=8),
    registry_path: Optional[str] = Query(None),
    edge_type: Optional[str] = Query(None),
    command_line: Optional[str] = Query(None)
):

    try:
        score_2b = ScoringEngine.score_channel_2b(
            edge_entropy=edge_entropy,
            registry_path=registry_path,
            edge_type=edge_type,
            command_line=command_line,
        )

        p_matrix_context = {
            "registry_path": registry_path,
            "edge_type": edge_type,
            "command_line": command_line,
        }
        
        return {
            "channel": "2B",
            "edge_entropy": edge_entropy,
            "score": round(score_2b, 3),
            "p_matrix_context": p_matrix_context,
            "interpretation": {
                "entropy": edge_entropy,
                "baseline_mean": 5.0,
                "registry_service_signal": bool(registry_path or edge_type or command_line),
                "anomalous": score_2b > 0.5
            }
        }
    
    except Exception as e:
        logger.error(f"  Failed to score channel 2B: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/score-channel-2c")
async def score_channel_2c(
    node_count: int = Query(..., ge=0),
    edge_count: int = Query(..., ge=0),
    max_depth: int = Query(0, ge=0),
    branching_factor: float = Query(0.0, ge=0)
):

    try:
        graph_features = {
            "node_count": node_count,
            "edge_count": edge_count,
            "max_depth": max_depth,
            "branching_factor": branching_factor
        }
        
        score_2c = ScoringEngine.score_channel_2c(graph_features)
        
        return {
            "channel": "2C",
            "graph_features": graph_features,
            "score": round(score_2c, 3),
            "interpretation": {
                "anomalous": score_2c > 0.6
            }
        }
    
    except Exception as e:
        logger.error(f"  Failed to score channel 2C: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decide-severity")
async def decide_severity(
    has_injection: bool = False,
    has_amsi_disable: bool = False,
    score_2a: float = Query(..., ge=0, le=1),
    score_2b: float = Query(..., ge=0, le=1),
    score_2c: float = Query(..., ge=0, le=1)
):

    try:
        severity = VotingEngine.decide_severity(
            has_injection,
            has_amsi_disable,
            score_2a,
            score_2b,
            score_2c
        )
        
        # Confidence
        confidence = VotingEngine.calculate_confidence(score_2a, score_2b, score_2c)
        
        return {
            "severity": severity.value,
            "confidence": round(confidence, 3),
            "scores": {
                "2a_math_certainty": round(score_2a, 3),
                "2b_statistical": round(score_2b, 3),
                "2c_ml_anomaly": round(score_2c, 3)
            },
            "signals": {
                "injection_detected": has_injection,
                "amsi_disabled": has_amsi_disable
            },
            "description": {
                "BENIGN": "No anomalies detected",
                "UNKNOWN": "Weak signals, requires investigation",
                "WARNING": "Suspicious behavior detected",
                "CRITICAL": "Strong indicators of compromise"
            }.get(severity.value, "Unknown")
        }
    
    except Exception as e:
        logger.error(f"  Failed to decide severity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_scoring_stats(db: Session = Depends(get_db)):
    try:
        total_edges = db.query(Edge).count()
        
        # Count by severity
        severity_dist = {}
        for severity in ["CRITICAL", "WARNING", "UNKNOWN", "BENIGN"]:
            count = db.query(Edge).filter(Edge.final_severity == severity).count()
            severity_dist[severity] = count
        
        return {
            "total_edges_scored": total_edges,
            "severity_distribution": severity_dist,
            "model_channels": ["2A", "2B", "2C"],
            "voting_method": "Consensus with confidence weighting"
        }
    
    except Exception as e:
        logger.error(f"  Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ml/save_model")
async def save_model_now():
    try:
        # import inside to avoid circular imports at module import time
        from backend.layers.layer2_scoring.runtime_engine import _ML_LOCK, _ML_MODEL
        with _ML_LOCK:
            if _ML_MODEL is None:
                raise HTTPException(status_code=400, detail="No model loaded")
            model_path = os.path.join('backend', 'ml', 'models', 'river_windows_baseline.pkl')
            tmp_path = model_path + '.tmp'
            try:
                import pickle
                with open(tmp_path, 'wb') as f:
                    pickle.dump(_ML_MODEL, f)
                os.replace(tmp_path, model_path)
            except Exception as e:
                logger.error(f"Failed to save model: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        return {"saved": True, "path": model_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"save_model_now error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/latest")
async def get_live_latest(
    limit: int = Query(50, ge=1, le=500),
    suspicious_only: bool = Query(True),
    min_final_score: float = Query(0.50, ge=0.0, le=1.0),
):

    try:
        with LATEST_LOCK:
            items = list(LATEST_DECISIONS.values())

        # newest first
        items.sort(key=lambda x: x.get("ts", 0), reverse=True)

        def is_suspicious(it: dict) -> bool:
            fusion = (it or {}).get("fusion") or {}
            decision = fusion.get("decision") or "NORMAL"
            final_score = float(fusion.get("final_score") or 0.0)
            if decision in ("SUSPICIOUS", "MALWARE ALERT"):
                return True
            return final_score >= min_final_score

        filtered = []
        for it in items:
            if suspicious_only and not is_suspicious(it):
                continue

            evt = it.get("event", {}) or {}
            scores = it.get("scores", {}) or {}
            fusion = it.get("fusion", {}) or {}

            filtered.append({
                "event": {
                    "event_id": evt.get("event_id"),
                    "ts": evt.get("ts"),
                    "source": evt.get("source"),
                    "kind": evt.get("kind"),
                    "session_id": evt.get("session_id"),
                    "parent_process": evt.get("parent_process"),
                    "child_process": evt.get("child_process"),
                    "target_path": evt.get("target_path"),
                    "reg_target": evt.get("reg_target"),
                    "file_entropy": evt.get("file_entropy"),
                },
                "scores": {
                    "A": scores.get("A"),
                    "B": scores.get("B"),
                    "C": scores.get("C"),
                },
                "fusion": fusion,
                "ts": it.get("ts"),
            })

            if len(filtered) >= limit:
                break

        return {"total": len(filtered), "items": filtered}
    except Exception as e:
        logger.error(f"  Failed to get live latest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live/{event_id}")
async def get_live_event(event_id: str):
    try:
        with LATEST_LOCK:
            item = LATEST_DECISIONS.get(event_id)
        if not item:
            raise HTTPException(status_code=404, detail="event_id not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"  Failed to get live event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest_telemetry_event(event: dict):
    try:
        from backend.layers.layer2_scoring.event_stream import new_event_id
        import time

        # Auto-fill defaults
        if "event_id" not in event:
            event["event_id"] = new_event_id()
        if "ts" not in event:
            event["ts"] = time.time()
        if "source" not in event:
            event["source"] = "sysmon"

        # Create TelemetryEvent and publish to queues
        evt = TelemetryEvent(**event)
        publish_event(evt)

        logger.info(f"[INGEST] Received event: {event.get('kind')} from {event.get('child_process')}")
        return {"status": "queued", "event_id": evt.event_id}
    except Exception as e:
        logger.error(f"  Failed to ingest event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/stream")
async def debug_stream():
    return {
        "queues": {
            "event": event_stream.EVENT_QUEUE.qsize(),
            "scoring": event_stream.SCORING_QUEUE.qsize(),
            "graph": event_stream.GRAPH_QUEUE.qsize(),
        },
        "last_published_ts": event_stream.LAST_PUBLISHED_TS,
        "last_event": event_stream.LAST_EVENT,
        "latest_decisions": len(LATEST_DECISIONS),
    }


@router.get("/debug/collector")
async def debug_collector(request: Request):
    sysmon = getattr(request.app.state, "sysmon", None)
    if not sysmon:
        return {"enabled": False, "error": "sysmon_not_initialized"}
    try:
        return sysmon.get_status()
    except Exception as e:
        return {"enabled": False, "error": str(e)}


@router.get("/debug/collector/recent")
async def debug_collector_recent(request: Request, limit: int = Query(5, ge=1, le=20)):
    sysmon = getattr(request.app.state, "sysmon", None)
    if not sysmon:
        return {"enabled": False, "error": "sysmon_not_initialized"}
    try:
        return sysmon.get_recent_events(limit=limit)
    except Exception as e:
        return {"enabled": False, "error": str(e)}


@router.get("/debug/engine")
async def debug_engine(request: Request):
    engine = getattr(request.app.state, "layer2_engine", None)
    thread_alive = False
    if engine and getattr(engine, "_thread", None):
        thread_alive = bool(engine._thread.is_alive())
    return {
        "engine_initialized": engine is not None,
        "thread_alive": thread_alive,
        "latest_decisions": len(LATEST_DECISIONS),
    }