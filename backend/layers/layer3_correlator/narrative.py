# backend/layers/layer3_correlator/narrative.py
"""
Layer 3: Narrative Generation
Creates plain-English descriptions of attack chains
"""

from backend.database.models import Edge, Node
from backend.shared.enums import Severity, EdgeType
from backend.shared.logger import setup_logger

logger = setup_logger(__name__)


class NarrativeGenerator:
    """Generate human-readable narratives from attack chains"""
    
    @staticmethod
    def generate(edges: list, severity: Severity) -> str:
        """
        Generate plain-English narrative from edges.
        
        Args:
            edges: List of Edge objects
            severity: Severity level
            
        Returns:
            Narrative string
        """
        try:
            if not edges:
                return "No activity detected."
            
            # Build narrative based on severity
            if severity == Severity.CRITICAL:
                narrative = NarrativeGenerator._generate_critical(edges)
            elif severity == Severity.WARNING:
                narrative = NarrativeGenerator._generate_warning(edges)
            elif severity == Severity.UNKNOWN:
                narrative = NarrativeGenerator._generate_unknown(edges)
            else:
                narrative = NarrativeGenerator._generate_benign(edges)
            
            logger.debug(f"  Generated narrative ({severity.value}): {narrative[:100]}...")
            return narrative
        
        except Exception as e:
            logger.error(f"  Failed to generate narrative: {e}")
            return "Unable to generate narrative."
    
    @staticmethod
    def _generate_critical(edges: list) -> str:
        """Generate narrative for CRITICAL incidents."""
        try:
            # Check for injection
            injection_edges = [e for e in edges if e.edge_type == EdgeType.INJECTED_INTO]
            if injection_edges:
                return f"  CRITICAL: Code injection detected. {len(injection_edges)} injection event(s) observed in process chain. Immediate isolation recommended."
            
            # Generic critical
            return f"  CRITICAL: Multiple anomalous behaviors detected across {len(edges)} events in process chain. High confidence of compromise."
        
        except Exception as e:
            logger.error(f"  Failed to generate critical narrative: {e}")
            return "CRITICAL: Anomalous behavior detected."
    
    @staticmethod
    def _generate_warning(edges: list) -> str:
        """Generate narrative for WARNING incidents."""
        try:
            # Check for script execution
            script_edges = [e for e in edges if e.edge_type == EdgeType.EXECUTED_SCRIPT]
            if script_edges:
                return f"  WARNING: Script execution detected. {len(script_edges)} script execution event(s). Recommend manual investigation."
            
            # Check for WMI
            wmi_edges = [e for e in edges if e.edge_type == EdgeType.SUBSCRIBED_WMI]
            if wmi_edges:
                return f"  WARNING: WMI subscriptions created. {len(wmi_edges)} WMI event(s). May indicate persistence technique."
            
            # Check for registry modifications
            reg_edges = [e for e in edges if e.edge_type == EdgeType.MODIFIED_REG]
            if reg_edges:
                return f"  WARNING: Registry modifications detected. {len(reg_edges)} registry event(s). Suspicious modification patterns."
            
            # Generic warning
            return f"  WARNING: Suspicious behavior detected. {len(edges)} event(s) show anomalous patterns requiring investigation."
        
        except Exception as e:
            logger.error(f"  Failed to generate warning narrative: {e}")
            return "WARNING: Suspicious behavior detected."
    
    @staticmethod
    def _generate_unknown(edges: list) -> str:
        """Generate narrative for UNKNOWN incidents."""
        try:
            spawn_count = len([e for e in edges if e.edge_type == EdgeType.SPAWNED])
            read_count = len([e for e in edges if e.edge_type == EdgeType.READ])
            write_count = len([e for e in edges if e.edge_type == EdgeType.WROTE])
            
            return f"🟠 UNKNOWN: Process chain with {spawn_count} spawned processes, {read_count} file reads, {write_count} file writes. Requires further analysis."
        
        except Exception as e:
            logger.error(f"  Failed to generate unknown narrative: {e}")
            return "UNKNOWN: Behavior requires investigation."
    
    @staticmethod
    def _generate_benign(edges: list) -> str:
        """Generate narrative for BENIGN incidents."""
        return f"   BENIGN: Process chain with {len(edges)} event(s). No anomalies detected. Normal system activity."
    
    @staticmethod
    def summarize_chain(nodes: list, edges: list) -> str:
        """
        Summarize process chain: svchost → explorer → script → powershell
        
        Args:
            nodes: List of nodes
            edges: List of edges
            
        Returns:
            Chain summary string
        """
        try:
            # Build chain from root to leaf
            if not edges:
                return "No chain."
            
            # Get root processes (no SPAWNED edge pointing to them)
            spawned_targets = set(e.target_id for e in edges if e.edge_type == EdgeType.SPAWNED)
            root_ids = [n.id for n in nodes if n.type.value == "process" and n.id not in spawned_targets]
            
            if not root_ids:
                return f"{len(nodes)} nodes, {len(edges)} edges"
            
            # Build chains from roots
            chains = []
            for root_id in root_ids:
                chain = NarrativeGenerator._trace_chain(root_id, edges, nodes)
                chains.append(" → ".join(chain))
            
            return " | ".join(chains) if chains else f"{len(nodes)} nodes"
        
        except Exception as e:
            logger.error(f"  Failed to summarize chain: {e}")
            return f"{len(nodes)} nodes, {len(edges)} edges"
    
    @staticmethod
    def _trace_chain(node_id: int, edges: list, nodes: list, depth: int = 0) -> list:
        """Recursively trace process chain."""
        try:
            if depth > 10:  # Prevent infinite recursion
                return []
            
            node = next((n for n in nodes if n.id == node_id), None)
            if not node:
                return []
            
            current = [node.name[:20]]  # Truncate name
            
            # Find children spawned by this node
            children = [e.target_id for e in edges if e.source_id == node_id and e.edge_type == EdgeType.SPAWNED]
            
            if children:
                for child_id in children[:2]:  # Limit to 2 children
                    child_chain = NarrativeGenerator._trace_chain(child_id, edges, nodes, depth + 1)
                    if child_chain:
                        current.extend(child_chain)
            
            return current
        
        except Exception as e:
            logger.error(f"  Failed to trace chain: {e}")
            return []