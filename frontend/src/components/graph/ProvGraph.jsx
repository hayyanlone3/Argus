// src/components/graph/ProvGraph.jsx
import React, { useEffect, useState } from 'react';
import { graphService } from '../../services/graphService';
import LoadingSpinner from '../common/LoadingSpinner';
import EdgeLegend from './EdgeLegend';

export default function ProvGraph() {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        setLoading(true);
        const nodesData = await graphService.getNodes(100);
        const edgesData = await graphService.getEdges(100);
        setNodes(nodesData.nodes || []);
        setEdges(edgesData.edges || []);
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

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="card border border-critical text-critical">Error: {error}</div>;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-bold text-lg">Provenance Graph</h3>
        <span className="text-sm text-gray-600">
          {nodes.length} nodes • {edges.length} edges
        </span>
      </div>

      <div className="bg-gray-100 rounded-lg p-4 min-h-96 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-2">🌳 Graph Visualization</p>
          <p className="text-sm text-gray-500">
            Live graph rendering • {nodes.length} active nodes
          </p>
        </div>
      </div>

      <EdgeLegend />

      <div className="mt-4">
        <h4 className="font-semibold text-sm mb-2">Recent Edges</h4>
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {edges.slice(0, 10).map((edge) => (
            <div key={edge.id} className="text-xs bg-gray-50 p-2 rounded">
              <span className="font-mono">{edge.source_id}</span> →
              <span className="font-mono text-critical ml-1">{edge.edge_type}</span> →
              <span className="font-mono ml-1">{edge.target_id}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}