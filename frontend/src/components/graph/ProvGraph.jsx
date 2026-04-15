import React, { useEffect, useMemo, useState } from 'react';
import { graphService } from '../../services/graphService';
import LoadingSpinner from '../common/LoadingSpinner';
import EdgeLegend from './EdgeLegend';
import D3ProvenanceGraph from './D3ProvenanceGraph';
import NodeDetail from './NodeDetail';

// All possible edge types for the UI toggle buttons
const ALL_EDGE_TYPES = [
  "SPAWNED",
  "WROTE",
  "MODIFIED_REG",
  "EXECUTED_SCRIPT",
  "INJECTED_INTO",
  "READ",
  "SUBSCRIBED_WMI",
  "DISABLED_AMSI",
];

// Initial state: only show process-centric edges to reduce noise
const DEFAULT_EDGE_TYPES = new Set([
  "SPAWNED",
  "INJECTED_INTO",
  "EXECUTED_SCRIPT",
  "MODIFIED_REG",
  // keep WROTE optional (massive)
  // "WROTE",
]);

export default function ProvGraph() {
  // full dataset (never mutate on node click)
  const [allNodes, setAllNodes] = useState([]);
  const [allEdges, setAllEdges] = useState([]);

  // view dataset (changes on focus)
  const [viewNodes, setViewNodes] = useState([]);
  const [viewEdges, setViewEdges] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [edgeTypeFilter, setEdgeTypeFilter] = useState(DEFAULT_EDGE_TYPES);

  const filteredViewEdges = useMemo(() => {
    if (!edgeTypeFilter || edgeTypeFilter.size === 0) return viewEdges;
    return (viewEdges || []).filter(e => edgeTypeFilter.has(e.edge_type));
  }, [viewEdges, edgeTypeFilter]);

  // keep only nodes referenced by filtered edges (reduces noise)
  const filteredViewNodes = useMemo(() => {
    const ids = new Set();
    filteredViewEdges.forEach(e => {
      ids.add(e.source_id);
      ids.add(e.target_id);
    });
    return (viewNodes || []).filter(n => ids.has(n.id));
  }, [viewNodes, filteredViewEdges]);

  const fetchGraph = async () => {
    const nodesData = await graphService.getNodes(250);
    const edgesData = await graphService.getEdges(250);

    const nodesArr = Array.isArray(nodesData) ? nodesData : (nodesData?.nodes || []);
    const edgesArr = Array.isArray(edgesData) ? edgesData : (edgesData?.edges || []);

    setAllNodes(nodesArr);
    setAllEdges(edgesArr);

    // default view = full
    setViewNodes(nodesArr);
    setViewEdges(edgesArr);
  };

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        await fetchGraph();
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    run();
    const interval = setInterval(run, 15000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onToggleEdgeType = (t) => {
    setEdgeTypeFilter(prev => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  };

  const focusNeighborhood = async (nodeId) => {
    try {
      const neigh = await graphService.getNeighbors(nodeId, 2);
      const neighborIds = new Set([nodeId, ...(neigh.neighbors || [])]);

      // IMPORTANT: build view from ALL data, not from previous (prevents “shrinking bug”)
      const nextNodes = (allNodes || []).filter(n => neighborIds.has(n.id));
      const nextEdges = (allEdges || []).filter(
        e => neighborIds.has(e.source_id) && neighborIds.has(e.target_id)
      );

      setViewNodes(nextNodes);
      setViewEdges(nextEdges);
    } catch (e) {
      console.warn("neighbors fetch failed", e);
      // keep existing view
    }
  };

  const onNodeClick = async (node) => {
    setSelectedNodeId(node?.id || null);
    if (node?.id) {
      await focusNeighborhood(node.id);
    }
  };

  const onReset = async () => {
    setSelectedNodeId(null);
    // reset view without refetching (fast)
    setViewNodes(allNodes);
    setViewEdges(allEdges);
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="card border border-red-600 text-red-600">Error: {error}</div>;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-bold text-lg">Provenance Graph</h3>
          <div className="text-xs text-gray-500">
            Click a node to focus its 2-hop neighborhood (stable: does not shrink permanently).
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="px-3 py-1 rounded bg-gray-900 text-white text-xs" onClick={onReset}>
            Reset
          </button>
          <span className="text-sm text-gray-600">
            {filteredViewNodes.length} nodes • {filteredViewEdges.length} edges
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-3">
        {ALL_EDGE_TYPES.map((t) => (
          <button
            key={t}
            onClick={() => onToggleEdgeType(t)}
            className={[
              "px-2 py-1 rounded text-xs border",
              edgeTypeFilter.has(t)
                ? "bg-blue-600 text-white border-blue-700"
                : "bg-white text-gray-700 border-gray-300",
            ].join(" ")}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2 bg-gray-50 rounded-lg p-2 border" style={{ minHeight: 560 }}>
          <D3ProvenanceGraph
            nodes={filteredViewNodes}
            edges={filteredViewEdges}
            height={560}
            onNodeClick={onNodeClick}
            selectedNodeId={selectedNodeId}
          />
        </div>

        <div className="bg-white rounded-lg border p-3 min-h-[560px]">
          <div className="font-semibold mb-2">Node Detail</div>
          {selectedNodeId ? (
            <NodeDetail nodeId={selectedNodeId} />
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