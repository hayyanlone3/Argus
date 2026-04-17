// src/pages/Layer3Dashboard.jsx
import React, { useEffect, useState } from 'react';
import IncidentFeed from '../components/incident/IncidentFeed';
import { incidentService } from '../services/incidentService';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function Layer3Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    const fetchStats = async (initial = false) => {
      try {
        if (initial) setLoading(true);
        const data = await incidentService.getStats();
        if (!mounted) return;
        setStats(data);
        setError(null);
      } catch (err) {
        if (!mounted) return;
        setError(err.message);
      } finally {
        if (!mounted) return;
        if (initial) setLoading(false);
      }
    };

    fetchStats(true);
    const interval = setInterval(() => fetchStats(false), 30000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1>🔗 Layer 3: Correlator</h1>
        <p className="text-gray-600">Group related events into incidents using 2-of-3 signals</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card">
            <p className="text-gray-600 text-sm mb-1">Total Incidents</p>
            <p className="text-3xl font-bold text-gray-900">{stats.total_incidents || 0}</p>
          </div>
          <div className="card">
            <p className="text-gray-600 text-sm mb-1">MTTI (Avg)</p>
            <p className="text-3xl font-bold text-red-600">
              {stats.metrics?.mean_time_to_identify_seconds
                ? `${Math.round(stats.metrics.mean_time_to_identify_seconds / 60)}m`
                : 'N/A'}
            </p>
          </div>
          <div className="card">
            <p className="text-gray-600 text-sm mb-1">FP Rate</p>
            <p className="text-3xl font-bold text-warning">
              {stats.metrics?.false_positive_rate_percent?.toFixed(1)}%
            </p>
          </div>
        </div>
      )}

      {/* Status Distribution */}
      {stats?.status_distribution && (
        <div className="card">
          <h3 className="font-bold text-lg mb-4">Status Distribution</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {Object.entries(stats.status_distribution).map(([status, count]) => (
              <div key={status} className="bg-gray-50 p-3 rounded-lg text-center">
                <p className="text-2xl font-bold text-red-600">{count}</p>
                <p className="text-xs text-gray-600">{status}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Correlation Signals */}
      <div className="card">
        <h3 className="font-bold text-lg mb-4">Correlation Signals (2-of-3)</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="border-2 border-blue-200 bg-blue-50 p-4 rounded-lg">
            <p className="font-semibold text-blue-900 mb-2">Signal 1: Graph Proximity</p>
            <p className="text-sm text-blue-800">Nodes within ≤2 hops in provenance graph</p>
          </div>
          <div className="border-2 border-green-200 bg-green-50 p-4 rounded-lg">
            <p className="font-semibold text-green-900 mb-2">Signal 2: Tree Root Match</p>
            <p className="text-sm text-green-800">Same process tree root (ultimate parent)</p>
          </div>
          <div className="border-2 border-purple-200 bg-purple-50 p-4 rounded-lg">
            <p className="font-semibold text-purple-900 mb-2">Signal 3: File Hash Match</p>
            <p className="text-sm text-purple-800">Same file SHA256 hash detected</p>
          </div>
        </div>
      </div>

      {/* Incident Feed */}
      <div>
        <h2>Recent Incidents</h2>
        <IncidentFeed limit={20} />
      </div>

      {/* Info */}
      <div className="card">
        <h3 className="font-bold text-lg mb-3">📖 About Layer 3</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li>✓ <strong>Grouping:</strong> Require 2 of 3 signals to group edges into incidents</li>
          <li>✓ <strong>MITRE Mapping:</strong> Auto-assign ATT&CK stages based on edge types</li>
          <li>✓ <strong>Narrative:</strong> Generate plain-English description of attack chain</li>
          <li>✓ <strong>Confidence:</strong> Score based on edge count and signal agreement</li>
        </ul>
      </div>
    </div>
  );
}