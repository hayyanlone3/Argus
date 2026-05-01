# backend/layers/layer3_correlator/services.py
from sqlalchemy.orm import Session
from typing import Optional
from backend.database.models import Edge, Node, Incident
from backend.database.schemas import IncidentCreate, IncidentResponse
from backend.shared.enums import Severity, EdgeType
from sqlalchemy import func
from backend.shared.logger import setup_logger
from backend.shared.constants import (
    CORRELATION_MAX_HOPS,
    CORRELATION_REQUIRE_SIGNALS,
    SIGNAL_PROXIMITY_WEIGHT,
    SIGNAL_TREE_ROOT_WEIGHT,
    SIGNAL_HASH_WEIGHT,
)
from datetime import datetime
import networkx as nx
import uuid

logger = setup_logger(__name__)


class CorrelatorService:
    """Layer 3: Session Correlator Service"""
    
    @staticmethod
    def check_graph_proximity(db: Session, node_id_1: int, node_id_2: int, max_hops: int) -> bool:
        try:
            from collections import deque
            
            queue = deque([(node_id_1, 0)])
            visited = {node_id_1}
            
            while queue:
                current_id, distance = queue.popleft()
                
                if current_id == node_id_2 and distance > 0:
                    return distance <= max_hops
                
                if distance >= max_hops:
                    continue
                neighbors = db.query(Edge.target_id).filter(
                    Edge.source_id == current_id
                ).limit(100).all()
                
                for (neighbor_id,) in neighbors:
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        queue.append((neighbor_id, distance + 1))
            
            return False
        
        except Exception as e:
            logger.error(f"  Failed to check proximity: {e}")
            return False
    
    @staticmethod
    def get_process_root(db: Session, process_node_id: int) -> int:
        try:
            current_id = process_node_id
            visited = set()
            max_iterations = 50  # Prevent infinite loops
            iterations = 0
            
            while current_id not in visited and iterations < max_iterations:
                visited.add(current_id)
                iterations += 1
                
                # Find parent via SPAWNED edges
                parent_edge = db.query(Edge).filter(
                    Edge.target_id == current_id,
                    Edge.edge_type == EdgeType.SPAWNED
                ).first()
                
                if not parent_edge:
                    return current_id
                
                current_id = parent_edge.source_id
            
            return current_id
        
        except Exception as e:
            logger.error(f"  Failed to get process root: {e}")
            return process_node_id
    
    @staticmethod
    def count_correlation_signals(db: Session, edge_1: Edge, edge_2: Edge) -> tuple:
        try:
            signals = 0
            confidence_sum = 0.0
            
            # Signal 1: Graph proximity
            if CorrelatorService.check_graph_proximity(db, edge_1.source_id, edge_2.source_id, CORRELATION_MAX_HOPS):
                signals += 1
                confidence_sum += SIGNAL_PROXIMITY_WEIGHT
                logger.debug(f"  Signal 1 (proximity): edges {edge_1.id} and {edge_2.id} are close")
            
            # Signal 2: Same process tree root
            node_1 = db.query(Node).filter(Node.id == edge_1.source_id).first()
            node_2 = db.query(Node).filter(Node.id == edge_2.source_id).first()
            
            if node_1 and node_2 and node_1.type.value == "process" and node_2.type.value == "process":
                root_1 = CorrelatorService.get_process_root(db, edge_1.source_id)
                root_2 = CorrelatorService.get_process_root(db, edge_2.source_id)
                
                if root_1 == root_2:
                    signals += 1
                    confidence_sum += SIGNAL_TREE_ROOT_WEIGHT
                    logger.debug(f"  Signal 2 (tree root): edges {edge_1.id} and {edge_2.id} share root")
            
            # Signal 3: Same file hash
            if edge_1.edge_metadata and edge_2.edge_metadata:
                if edge_1.edge_metadata.get("file_hash") == edge_2.edge_metadata.get("file_hash"):
                    signals += 1
                    confidence_sum += SIGNAL_HASH_WEIGHT
                    logger.debug(f"  Signal 3 (file hash): edges {edge_1.id} and {edge_2.id} match")
            
            return (signals, confidence_sum)
        
        except Exception as e:
            logger.error(f"  Failed to count signals: {e}")
            return (0, 0.0)
    
    @staticmethod
    def group_edges_by_signals(db: Session, edges: list) -> dict:
        try:
            groups = {}
            
            for edge in edges:
                best_group_id = None
                best_confidence = 0.0
                
                # Try to match with existing groups
                for group_id, group_edges in groups.items():
                    signals, confidence = CorrelatorService.count_correlation_signals(
                        db, edge, group_edges[0]
                    )
                    
                    if signals >= CORRELATION_REQUIRE_SIGNALS and confidence > best_confidence:
                        best_group_id = group_id
                        best_confidence = confidence
                
                # Add to best group or create new
                if best_group_id:
                    groups[best_group_id].append(edge)
                    logger.debug(f"Added edge {edge.id} to group {best_group_id}")
                else:
                    new_group_id = str(uuid.uuid4())[:8]
                    groups[new_group_id] = [edge]
                    logger.debug(f"Created group {new_group_id} with edge {edge.id}")
            
            logger.info(f"🔗 Grouped {len(edges)} edges into {len(groups)} incidents")
            return groups
        
        except Exception as e:
            logger.error(f"  Failed to group edges: {e}")
            return {}
    
    @staticmethod
    def create_incident_from_edges(db: Session, session_id: str, edges: list, severity: Severity) -> Incident:
        try:
            # Calculate confidence from signal count
            confidence = min(len(edges) / 10.0, 1.0)  # Confidence grows with chain length
            
            # Determine MITRE stage (simplified)
            mitre_stage = CorrelatorService.determine_mitre_stage(edges)
            
            # Generate narrative
            from .narrative import NarrativeGenerator
            narrative = NarrativeGenerator.generate(edges, severity)
            
            # Create incident
            incident = Incident(
                session_id=session_id,
                created_at=datetime.utcnow(),
                confidence=confidence,
                severity=severity,
                mitre_stage=mitre_stage,
                narrative=narrative,
                status="OPEN"
            )
            
            db.add(incident)
            db.commit()
            db.refresh(incident)
            logger.info(f"✨ Created incident: {session_id} ({severity.value}, {len(edges)} edges)")

            # Notify SSE subscribers about the new incident (best-effort, async)
            try:
                from . import broadcaster
                payload = IncidentResponse.from_orm(incident).dict()
                broadcaster.notify_incident(payload)
            except Exception as e:
                logger.debug(f"  SSE notify skipped: {e}")

            return incident
        
        except Exception as e:
            logger.error(f"  Failed to create incident: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def determine_mitre_stage(edges: list) -> str:
        try:
            # Count edge types
            edge_type_counts = {}
            for edge in edges:
                edge_type = edge.edge_type.value
                edge_type_counts[edge_type] = edge_type_counts.get(edge_type, 0) + 1
            
            # Map edge types to MITRE stages
            stage_mapping = {
                "SPAWNED": "Execution",
                "INJECTED_INTO": "Defense Evasion",
                "EXECUTED_SCRIPT": "Execution",
                "SUBSCRIBED_WMI": "Persistence",
                "MODIFIED_REG": "Persistence",
                "READ": "Discovery",
                "WROTE": "Discovery",
            }
            
            # Find most common stage
            stage_scores = {}
            for edge_type, count in edge_type_counts.items():
                stage = stage_mapping.get(edge_type, "Unknown")
                stage_scores[stage] = stage_scores.get(stage, 0) + count
            
            if stage_scores:
                primary_stage = max(stage_scores, key=stage_scores.get)
                logger.debug(f"🏷️  Primary MITRE stage: {primary_stage}")
                return primary_stage
            
            return "Unknown"
        
        except Exception as e:
            logger.error(f"  Failed to determine MITRE stage: {e}")
            return "Unknown"
    
    @staticmethod
    def get_incident_chain(db: Session, incident_id: int) -> dict:
        try:
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            
            if not incident:
                return {}
            
            # Get edges for this incident
            edges = db.query(Edge).filter(Edge.session_id == incident.session_id).all()
            
            # Get all unique nodes
            node_ids = set()
            for edge in edges:
                node_ids.add(edge.source_id)
                node_ids.add(edge.target_id)
            
            nodes = db.query(Node).filter(Node.id.in_(list(node_ids))).all()
            
            return {
                "incident": incident,
                "nodes": nodes,
                "edges": edges,
                "node_count": len(nodes),
                "edge_count": len(edges)
            }
        
        except Exception as e:
            logger.error(f"  Failed to get incident chain: {e}")
            return {}
    
    @staticmethod
    def upsert_incident_for_session(db: Session, session_id: str) -> Optional[Incident]:
        try:
            edges = db.query(Edge).filter(Edge.session_id == session_id).order_by(Edge.timestamp.asc()).all()
            if not edges:
                return None

            # Decide severity: max of severities present on edges
            order = {Severity.BENIGN: 0, Severity.UNKNOWN: 1, Severity.WARNING: 2, Severity.CRITICAL: 3}

            severities = [e.final_severity for e in edges if e.final_severity is not None]
            if not severities:
                return None

            max_sev = max(severities, key=lambda s: order.get(s, 0))

            # removed BENIGN skip to allow seeing all incidents in demo

            incident = db.query(Incident).filter(Incident.session_id == session_id).first()

            # Narrative + MITRE
            mitre_stage = CorrelatorService.determine_mitre_stage(edges)
            from .narrative import NarrativeGenerator
            narrative = NarrativeGenerator.generate(edges, max_sev)

            confidence = min(len(edges) / 10.0, 1.0)

            if incident is None:
                # Calculate AI detection time from first event
                first_event_time = edges[0].timestamp if edges else datetime.utcnow()
                detection_time = (datetime.utcnow() - first_event_time).total_seconds()
                
                incident = Incident(
                    session_id=session_id,
                    created_at=datetime.utcnow(),
                    confidence=confidence,
                    severity=max_sev,
                    mitre_stage=mitre_stage,
                    narrative=narrative,
                    status="OPEN",
                    first_event_timestamp=first_event_time,
                    detection_seconds=detection_time,
                )
                db.add(incident)
            else:
                # escalate severity if needed; refresh narrative
                incident.confidence = confidence
                incident.mitre_stage = mitre_stage
                incident.narrative = narrative
                if order.get(max_sev, 0) > order.get(incident.severity, 0):
                    incident.severity = max_sev

            db.commit()
            db.refresh(incident)
            
            # Log incident creation immediately
            if incident.severity in (Severity.CRITICAL, Severity.WARNING):
                logger.warning(f"[CORRELATOR] 🚨 {incident.severity.value} INCIDENT CREATED!")
                logger.warning(f"[CORRELATOR]   ID: {incident.id}")
                logger.warning(f"[CORRELATOR]   Session: {incident.session_id}")
                logger.warning(f"[CORRELATOR]   Edges: {len(edges)}")
                logger.warning(f"[CORRELATOR]   MITRE: {incident.mitre_stage}")
                if incident.detection_seconds is not None:
                    logger.warning(f"[CORRELATOR]   ⚡ AI Detection Time: {incident.detection_seconds:.2f}s")
                
                # Notify SSE subscribers about the new incident (best-effort, async)
                try:
                    from . import broadcaster
                    payload = IncidentResponse.from_orm(incident).dict()
                    broadcaster.notify_incident(payload)
                except Exception as e:
                    logger.debug(f"📡 SSE notify failed: {e}")
            
            return incident

        except Exception as e:
            logger.error(f"  upsert_incident_for_session failed: {e}")
            db.rollback()
            return None