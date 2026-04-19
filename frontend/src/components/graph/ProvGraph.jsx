// src/components/graph/ProvGraph.jsx
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
  const [refreshing, setRefreshing] = useState(false);
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

    // Cheap signatures to avoid re-layout flicker
    const nodesSig = `${nodesArr.length}:${nodesArr[0]?.id || ''}:${nodesArr[nodesArr.length - 1]?.id || ''}`;
    const edgesSig = `${edgesArr.length}:${edgesArr[0]?.id || ''}:${edgesArr[edgesArr.length - 1]?.id || ''}`;
    const sig = `${nodesSig}|${edgesSig}`;

    setAllNodes((prev) => {
      const prevSig = `${prev.length}:${prev[0]?.id || ''}:${prev[prev.length - 1]?.id || ''}`;
      return prevSig === nodesSig ? prev : nodesArr;
    });

    setAllEdges((prev) => {
      const prevSig = `${prev.length}:${prev[0]?.id || ''}:${prev[prev.length - 1]?.id || ''}`;
      return prevSig === edgesSig ? prev : edgesArr;
    });

    // default view = full (only if not focused)
    setViewNodes((prev) => (selectedNodeId ? prev : nodesArr));
    setViewEdges((prev) => (selectedNodeId ? prev : edgesArr));

    return sig;
  };

  useEffect(() => {
    let mounted = true;
    let lastSig = "";

    const run = async (initial = false) => {
      try {
        if (initial) setLoading(true);
        else {
            setRefreshing(true);
            setError(null);
        }

        const sig = await fetchGraph();

        // Build a cheap signature so we don't update state if nothing changed
        // (prevents D3 graph from re-layouting constantly)
        if (mounted && sig !== lastSig) {
          lastSig = sig;
        }
      } catch (err) {
        if (!mounted) return;
        setError(err.message);
      } finally {
        if (!mounted) return;
        if (initial) setLoading(false);
        else setRefreshing(false);
      }
    };

    run(true);
    const interval = setInterval(() => run(false), 30000); // was 15000; reduce load
    return () => {
      mounted = false;
      clearInterval(interval);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedNodeId]); // Re-bind closure to correctly check selectedNodeId in fetchGraph

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
          <div className="flex items-center gap-3">
              <h3 className="font-bold text-lg">Provenance Graph</h3>
              {refreshing && <span className="text-xs font-mono text-gray-400">syncing...</span>}
          </div>
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

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 bg-[#0f172a] rounded-2xl p-0 border border-slate-800 shadow-2xl relative overflow-hidden" style={{ minHeight: 600 }}>
          <D3ProvenanceGraph
            nodes={filteredViewNodes}
            edges={filteredViewEdges}
            height={600}
            onNodeClick={onNodeClick}
            selectedNodeId={selectedNodeId}
          />
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm min-h-[600px]">
          <div className="flex items-center gap-2 mb-4 pb-2 border-b border-slate-100">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
            <div className="font-black text-xs uppercase tracking-widest text-slate-400">Node Explorer</div>
          </div>
          {selectedNodeId ? (
            <NodeDetail nodeId={selectedNodeId} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-4 px-4">
              <div className="text-4xl filter grayscale opacity-20">🖱️</div>
              <div className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                Select a node in the graph to inspect provenance details
              </div>
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