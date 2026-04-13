# backend/layers/layer1_graph_engine/__init__.py
"""
Layer 1: Provenance Graph Engine
Constructs and manages the attack chain graph:
- Node creation (process, file, script, WMI, registry)
- Edge creation (SPAWNED, READ, WROTE, INJECTED_INTO, etc.)
- Active 24h window + 30-day queryable archive
- Graph traversal and correlation
"""

from .services import GraphService

__all__ = ["GraphService"]