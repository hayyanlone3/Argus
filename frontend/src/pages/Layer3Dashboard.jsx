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
        <h1>Layer 3: Correlator</h1>
        <p className="text-gray-600">Group related events into incidents using signals</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="card">
            <p className="text-gray-600 text-sm mb-1">Total Incidents</p>
            <p className="text-3xl font-bold text-gray-900">{stats.total_incidents || 0}</p>
          </div>
          
          {/* NEW: AI Detection Time */}
          <div className="card bg-linear-to-br from-green-50 to-green-100 border-2 border-green-200">
            <p className="text-gray-700 text-sm mb-1 font-semibold flex items-center gap-1">
              AI Detection Time
            </p>
            <p className="text-4xl font-bold text-green-600">
              {stats.metrics?.mean_detection_seconds !== undefined
                ? `${stats.metrics.mean_detection_seconds.toFixed(2)}s`
                : '0.00s'}
            </p>
            <p className="text-xs text-gray-600 mt-1">Average time to detect threat</p>
          </div>
          
          {/* KEEP: MTTI (Analyst Response) */}
          <div className="card bg-linear-to-br from-blue-50 to-blue-100 border-2 border-blue-200">
            <p className="text-gray-700 text-sm mb-1 font-semibold flex items-center gap-1">
              MTTI (Analyst)
            </p>
            <p className="text-4xl font-bold text-blue-600">
              {stats.metrics?.mean_time_to_identify_seconds
                ? `${Math.round(stats.metrics.mean_time_to_identify_seconds / 60)}m`
                : 'N/A'}
            </p>
            <p className="text-xs text-gray-600 mt-1">Time to analyst confirmation</p>
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

      <div>
        <h2>Recent Incidents</h2>
        <IncidentFeed limit={20} />
      </div>
    </div>
  );
}