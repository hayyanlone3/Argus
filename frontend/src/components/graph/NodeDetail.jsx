// src/components/graph/NodeDetail.jsx
import React, { useEffect, useState } from 'react';
import { graphService } from '../../services/graphService';
import LoadingSpinner from '../common/LoadingSpinner';

export default function NodeDetail({ nodeId }) {
  const [neighbors, setNeighbors] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchNeighbors = async () => {
      try {
        setLoading(true);
        const data = await graphService.getNeighbors(nodeId);
        setNeighbors(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    if (nodeId) {
      fetchNeighbors();
    }
  }, [nodeId]);

  if (!nodeId) return null;
  if (loading) return <LoadingSpinner />;
  if (error) return <div className="card border border-critical text-critical">Error: {error}</div>;

  return (
    <div className="card">
      <h4 className="font-bold mb-3">Node {neighbors?.node_id}</h4>

      <div className="space-y-2 text-sm">
        <p><strong>Name:</strong> {neighbors?.node_name}</p>
        <p><strong>Neighbors:</strong> {neighbors?.neighbor_count}</p>
        <p><strong>Hops:</strong> 2</p>
      </div>

      {neighbors?.neighbors && neighbors.neighbors.length > 0 && (
        <div className="mt-4 border-t pt-4">
          <h5 className="font-semibold text-sm mb-2">Connected Nodes</h5>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {neighbors.neighbors.map((nid) => (
              <div key={nid} className="text-xs bg-gray-50 p-2 rounded font-mono">
                Node {nid}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}