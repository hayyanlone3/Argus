// src/pages/Dashboard.jsx
import React, { useEffect, useState } from 'react';
import IncidentFeed from '../components/incident/IncidentFeed';
import { incidentService } from '../services/incidentService';
import { learningService } from '../services/learningService';
import LoadingSpinner from '../components/common/LoadingSpinner';
import SeverityBadge from '../components/common/SeverityBadge';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [learningStats, setLearningStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSeverity, setSelectedSeverity] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const [incidentStats, learningData] = await Promise.all([
          incidentService.getStats(),
          learningService.getStats(),
        ]);
        setStats(incidentStats);
        setLearningStats(learningData);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <LoadingSpinner />;

  const severityOrder = ['CRITICAL', 'WARNING', 'UNKNOWN', 'BENIGN'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1>🎯 Dashboard</h1>
        <p className="text-gray-600">Provenance Graph Anomaly Detection System • Live Monitoring</p>
      </div>

      {/* Key Metrics */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {severityOrder.map((severity) => (
            <div key={severity} className="card">
              <p className="text-gray-600 text-sm mb-1">{severity}</p>
              <p className="text-4xl font-bold text-gray-900 mb-2">
                {stats.severity_distribution?.[severity] || 0}
              </p>
              <SeverityBadge severity={severity} />
            </div>
          ))}
        </div>
      )}

      {/* Quick Stats */}
      {stats && learningStats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card">
            <p className="text-gray-600 text-sm mb-1">Model Maturity</p>
            <p className="text-3xl font-bold text-critical mb-1">
              {learningStats.weekly_stats?.data_quality_percent?.toFixed(0) || 0}%
            </p>
            <p className="text-xs text-gray-600">Analyst feedback rate</p>
          </div>

          <div className="card">
            <p className="text-gray-600 text-sm mb-1">False Positive Rate</p>
            <p className="text-3xl font-bold text-warning mb-1">
              {learningStats.weekly_stats?.fp_rate_percent?.toFixed(1) || 0}%
            </p>
            <p className="text-xs text-gray-600">Weekly metric</p>
          </div>

          <div className="card">
            <p className="text-gray-600 text-sm mb-1">Open Incidents</p>
            <p className="text-3xl font-bold text-unknown mb-1">
              {stats.status_distribution?.OPEN || 0}
            </p>
            <p className="text-xs text-gray-600">Requires action</p>
          </div>
        </div>
      )}

      {/* Severity Filter */}
      <div className="flex gap-2">
        <button
          onClick={() => setSelectedSeverity(null)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            selectedSeverity === null
              ? 'bg-critical text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          All Incidents
        </button>
        {['CRITICAL', 'WARNING', 'UNKNOWN', 'BENIGN'].map((sev) => (
          <button
            key={sev}
            onClick={() => setSelectedSeverity(sev)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              selectedSeverity === sev
                ? 'bg-critical text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {sev}
          </button>
        ))}
      </div>

      {/* Incident Feed */}
      <div>
        <h2>Incident Feed</h2>
        <IncidentFeed severity={selectedSeverity} limit={20} />
      </div>

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          💡 <strong>Tip:</strong> Click any incident card to view details, graph chain, and submit analyst feedback.
        </p>
      </div>
    </div>
  );
}