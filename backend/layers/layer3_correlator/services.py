# backend/layers/layer3_correlator/services.py
"""
Layer 3: Correlator Service
Groups edges into incidents using 2-of-3 signal correlation
"""

from sqlalchemy.orm import Session
from database.models import Edge, Node, Incident
from database.schemas import IncidentCreate
from shared.enums import Severity, EdgeType
from shared.logger import setup_logger
from shared.constants import (
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
        """
        Check if two nodes are within N hops (graph proximity).
        
        Args:
            db: Database session
            node_id_1, node_id_2: Node IDs to compare
            max_hops: Maximum hops allowed
            
        Returns:
            True if nodes are <=max_hops apart
        """
        try:
            edges = db.query(Edge).all()
            G = nx.DiGraph()
            for edge in edges:
                G.add_edge(edge.source_id, edge.target_id)
            
            if node_id_1 not in G or node_id_2 not in G:
                return False
            
            try:
                distance = nx.shortest_path_length(G, node_id_1, node_id_2)
                return distance <= max_hops
            except nx.NetworkXNoPath:
                return False
        
        except Exception as e:
            logger.error(f"❌ Failed to check proximity: {e}")
            return False
    
    @staticmethod
    def get_process_root(db: Session, process_node_id: int) -> int:
        """
        Get root parent of process tree (ultimate parent process).
        
        Args:
            db: Database session
            process_node_id: Process node ID
            
        Returns:
            Root process node ID
        """
        try:
            current_id = process_node_id
            visited = set()
            
            while current_id not in visited:
                visited.add(current_id)
                
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
            logger.error(f"❌ Failed to get process root: {e}")
            return process_node_id
    
    @staticmethod
    def count_correlation_signals(db: Session, edge_1: Edge, edge_2: Edge) -> tuple:
        """
        Count correlation signals between two edges (2 of 3 needed).
        
        Signals:
        1. Graph proximity (≤2 hops)
        2. Same process tree root
        3. Same file hash
        
        Args:
            db: Database session
            edge_1, edge_2: Edge objects to correlate
            
        Returns:
            (signal_count: int, confidence: float)
        """
        try:
            signals = 0
            confidence_sum = 0.0
            
            # Signal 1: Graph proximity
            if CorrelatorService.check_graph_proximity(db, edge_1.source_id, edge_2.source_id, CORRELATION_MAX_HOPS):
                signals += 1
                confidence_sum += SIGNAL_PROXIMITY_WEIGHT
                logger.debug(f"✅ Signal 1 (proximity): edges {edge_1.id} and {edge_2.id} are close")
            
            # Signal 2: Same process tree root
            node_1 = db.query(Node).filter(Node.id == edge_1.source_id).first()
            node_2 = db.query(Node).filter(Node.id == edge_2.source_id).first()
            
            if node_1 and node_2 and node_1.type.value == "process" and node_2.type.value == "process":
                root_1 = CorrelatorService.get_process_root(db, edge_1.source_id)
                root_2 = CorrelatorService.get_process_root(db, edge_2.source_id)
                
                if root_1 == root_2:
                    signals += 1
                    confidence_sum += SIGNAL_TREE_ROOT_WEIGHT
                    logger.debug(f"✅ Signal 2 (tree root): edges {edge_1.id} and {edge_2.id} share root")
            
            # Signal 3: Same file hash
            if edge_1.edge_metadata and edge_2.edge_metadata:
                if edge_1.edge_metadata.get("file_hash") == edge_2.edge_metadata.get("file_hash"):
                    signals += 1
                    confidence_sum += SIGNAL_HASH_WEIGHT
                    logger.debug(f"✅ Signal 3 (file hash): edges {edge_1.id} and {edge_2.id} match")
            
            return (signals, confidence_sum)
        
        except Exception as e:
            logger.error(f"❌ Failed to count signals: {e}")
            return (0, 0.0)
    
    @staticmethod
    def group_edges_by_signals(db: Session, edges: list) -> dict:
        """
        Group edges by correlation signals (2-of-3 required).
        
        Args:
            db: Database session
            edges: List of Edge objects
            
        Returns:
            {
                group_id: [edges in group],
                ...
            }
        """
        try:
            groups = {}
            
            for edge in edges:
                best_group_id = None
                best_confidence = 0.0
                
                # Try to match with existing groups
                for group_id, group_edges in groups.items():
                    # Check correlation with first edge in group
                    signals, confidence = CorrelatorService.count_correlation_signals(
                        db, edge, group_edges[0]
                    )
                    
                    # Require 2+ signals
                    if signals >= CORRELATION_REQUIRE_SIGNALS and confidence > best_confidence:
                        best_group_id = group_id
                        best_confidence = confidence
                
                # Add to best group or create new
                if best_group_id:
                    groups[best_group_id].append(edge)
                    logger.debug(f"📌 Added edge {edge.id} to group {best_group_id}")
                else:
                    new_group_id = str(uuid.uuid4())[:8]
                    groups[new_group_id] = [edge]
                    logger.debug(f"📌 Created group {new_group_id} with edge {edge.id}")
            
            logger.info(f"🔗 Grouped {len(edges)} edges into {len(groups)} incidents")
            return groups
        
        except Exception as e:
            logger.error(f"❌ Failed to group edges: {e}")
            return {}
    
    @staticmethod
    def create_incident_from_edges(db: Session, session_id: str, edges: list, severity: Severity) -> Incident:
        """
        Create incident from grouped edges.
        
        Args:
            db: Database session
            session_id: Unique session ID
            edges: List of Edge objects in this incident
            severity: Severity level
            
        Returns:
            Incident object
        """
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
            return incident
        
        except Exception as e:
            logger.error(f"❌ Failed to create incident: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def determine_mitre_stage(edges: list) -> str:
        """
        Determine primary MITRE ATT&CK stage from edge types.
        
        Args:
            edges: List of Edge objects
            
        Returns:
            MITRE stage string
        """
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
                "DISABLED_AMSI": "Defense Evasion",
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
            logger.error(f"❌ Failed to determine MITRE stage: {e}")
            return "Unknown"
    
    @staticmethod
    def get_incident_chain(db: Session, incident_id: int) -> dict:
        """
        Get full incident chain: all nodes and edges.
        
        Args:
            db: Database session
            incident_id: Incident ID
            
        Returns:
            {
                "incident": Incident,
                "nodes": [Node],
                "edges": [Edge]
            }
        """
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
            logger.error(f"❌ Failed to get incident chain: {e}")
            return {}