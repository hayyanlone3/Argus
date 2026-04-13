// src/pages/Layer1Dashboard.jsx
import React, { useEffect, useState } from 'react';
import ProvGraph from '../components/graph/ProvGraph';
import { graphService } from '../services/graphService';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function Layer1Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const data = await graphService.getStats();
        setStats(data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 20000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6 bg-gray-100 min-h-screen p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-6 h-6 bg-green-500 rounded flex items-center justify-center text-white text-sm">
            ✓
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Layer 1: Graph Engine</h1>
        </div>
        <p className="text-gray-600 text-sm">Provenance graph construction and event correlation</p>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="metric-card">
            <div className="metric-label">Total Nodes</div>
            <div className="metric-value">{stats.total_nodes || 0}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Total Edges</div>
            <div className="metric-value">{stats.total_edges || 0}</div>
          </div>
          <div className="metric-card border-l-4 border-red-500">
            <div className="metric-label">Active (24h)</div>
            <div className="metric-value text-red-600">{stats.active_edges_24h || 0}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Window</div>
            <div className="metric-value">24h</div>
          </div>
        </div>
      )}

      {/* Node Types */}
      {stats?.node_breakdown && (
        <div className="card">
          <h3 className="section-header">Node Types</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(stats.node_breakdown).map(([type, count]) => (
              <div key={type} className="grid-item">
                <div className="grid-item-value">{count}</div>
                <div className="grid-item-label capitalize">{type}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edge Types */}
      {stats?.edge_breakdown && (
        <div className="card">
          <h3 className="section-header">Edge Types</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(stats.edge_breakdown).map(([type, count]) => (
              <div key={type} className="grid-item">
                <div className="grid-item-value text-blue-600">{count}</div>
                <div className="grid-item-colored">{type}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Graph Visualization */}
      <ProvGraph />

      {/* Info Section */}
      <div className="card border-l-4 border-green-500 bg-green-50">
        <h3 className="section-header text-green-900">About Layer 1</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li className="flex items-start gap-2">
            <span className="text-green-600 font-bold">✓</span>
            <span><strong>Event Collection:</strong> ETW, Threat Intel, AMSI, Registry, WMI</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-600 font-bold">✓</span>
            <span><strong>Node Types:</strong> Process, File, Script, WMI Object, Registry Key</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-600 font-bold">✓</span>
            <span><strong>Edge Types:</strong> SPAWNED, READ, WROTE, INJECTED_INTO, and more</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-green-600 font-bold">✓</span>
            <span><strong>Active Window:</strong> 24 hours in-memory, 30 days queryable archive</span>
          </li>
        </ul>
      </div>
    </div>
  );
}