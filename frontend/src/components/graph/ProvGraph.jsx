import React, { useEffect, useMemo, useState } from 'react';
import { graphService } from '../../services/graphService';
import LoadingSpinner from '../common/LoadingSpinner';
import EdgeLegend from './EdgeLegend';
import D3ProvenanceGraph from './D3ProvenanceGraph';
import NodeDetail from './NodeDetail';

const DEFAULT_EDGE_TYPES = new Set([
  "SPAWNED",
  "WROTE",
  "MODIFIED_REG",
  "EXECUTED_SCRIPT",
  "INJECTED_INTO",
  "READ",
  "SUBSCRIBED_WMI",
  "DISABLED_AMSI",
]);

export default function ProvGraph() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedNode, setSelectedNode] = useState(null);
  const [edgeTypeFilter, setEdgeTypeFilter] = useState(DEFAULT_EDGE_TYPES);

  const filteredEdges = useMemo(() => {
    if (!edgeTypeFilter || edgeTypeFilter.size === 0) return edges;
    return (edges || []).filter(e => edgeTypeFilter.has(e.edge_type));
  }, [edges, edgeTypeFilter]);

  // keep only nodes referenced by filtered edges (reduces noise)
  const filteredNodes = useMemo(() => {
    const ids = new Set();
    filteredEdges.forEach(e => {
      ids.add(e.source_id);
      ids.add(e.target_id);
    });
    return (nodes || []).filter(n => ids.has(n.id));
  }, [nodes, filteredEdges]);

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        setLoading(true);
        const nodesData = await graphService.getNodes(200);
        const edgesData = await graphService.getEdges(200);

        setNodes(Array.isArray(nodesData) ? nodesData : (nodesData?.nodes || []));
        setEdges(Array.isArray(edgesData) ? edgesData : (edgesData?.edges || []));
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchGraph();
    const interval = setInterval(fetchGraph, 15000);
    return () => clearInterval(interval);
  }, []);

  const onToggleEdgeType = (t) => {
    setEdgeTypeFilter(prev => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  };

  const onNodeClick = async (node) => {
    setSelectedNode(node);
    try {
      // Expand neighborhood subgraph around the clicked node
      const neigh = await graphService.getNeighbors(node.id, 2);
      const neighborIds = new Set([node.id, ...(neigh.neighbors || [])]);

      // Keep only nodes in neighborhood
      setNodes(prev => (prev || []).filter(n => neighborIds.has(n.id)));
      // Keep only edges fully inside neighborhood
      setEdges(prev => (prev || []).filter(e => neighborIds.has(e.source_id) && neighborIds.has(e.target_id)));
    } catch (e) {
      // If neighbor endpoint fails, don't break UX
      console.warn("neighbors fetch failed", e);
    }
  };

  const onReset = async () => {
    setSelectedNode(null);
    setLoading(true);
    try {
      const nodesData = await graphService.getNodes(200);
      const edgesData = await graphService.getEdges(200);
      setNodes(Array.isArray(nodesData) ? nodesData : (nodesData?.nodes || []));
      setEdges(Array.isArray(edgesData) ? edgesData : (edgesData?.edges || []));
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="card border border-red-600 text-red-600">Error: {error}</div>;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-bold text-lg">Provenance Graph</h3>
          <div className="text-xs text-gray-500">
            Click a node to focus its 2-hop neighborhood (process → child → writes → reg keys).
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="px-3 py-1 rounded bg-gray-900 text-white text-xs" onClick={onReset}>
            Reset
          </button>
          <span className="text-sm text-gray-600">
            {filteredNodes.length} nodes • {filteredEdges.length} edges
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-3">
        {Array.from(DEFAULT_EDGE_TYPES).map((t) => (
          <button
            key={t}
            onClick={() => onToggleEdgeType(t)}
            className={[
              "px-2 py-1 rounded text-xs border",
              edgeTypeFilter.has(t) ? "bg-blue-600 text-white border-blue-700" : "bg-white text-gray-700 border-gray-300"
            ].join(" ")}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2 bg-gray-50 rounded-lg p-2 border" style={{ minHeight: 560 }}>
          <D3ProvenanceGraph
            nodes={filteredNodes}
            edges={filteredEdges}
            height={560}
            onNodeClick={onNodeClick}   // NEW
            selectedNodeId={selectedNode?.id} // NEW (highlight)
          />
        </div>

        <div className="bg-white rounded-lg border p-3 min-h-[560px]">
          <div className="font-semibold mb-2">Node Detail</div>
          {selectedNode ? (
            <NodeDetail node={selectedNode} />
          ) : (
            <div className="text-sm text-gray-500">
              Click a node in the graph to see details and auto-focus its neighborhood.
            </div>
          )}
        </div>
      </div>

      <div className="mt-3">
        <EdgeLegend />
      </div>
    </div>
  );
}