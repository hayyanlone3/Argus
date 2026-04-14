// src/pages/IncidentDetail.jsx
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { incidentService } from '../services/incidentService';
import LoadingSpinner from '../components/common/LoadingSpinner';
import SeverityBadge from '../components/common/SeverityBadge';
import IncidentActions from '../components/incident/IncidentActions';
import ProvGraph from '../components/graph/ProvGraph';
import { formatDate, formatHash } from '../utils/formatters';

export default function IncidentDetail() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [incident, setIncident] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchIncident = async () => {
    try {
      setLoading(true);
      const data = await incidentService.getIncident(sessionId);
      setIncident(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncident();
    const interval = setInterval(fetchIncident, 10000);
    return () => clearInterval(interval);
  }, [sessionId]);

  if (loading) return <LoadingSpinner />;
  if (error) return (
    <div className="space-y-4">
      <button onClick={() => navigate('/')} className="btn-secondary">
        ← Back
      </button>
      <div className="card border border-red-600 text-red-600">Error: {error}</div>
    </div>
  );

  if (!incident?.incident) return (
    <div className="space-y-4">
      <button onClick={() => navigate('/')} className="btn-secondary">
        ← Back
      </button>
      <div className="card">Incident not found</div>
    </div>
  );

  const inc = incident.incident;

  return (
    <div className="space-y-6">
      {/* Header */}
      <button onClick={() => navigate('/')} className="btn-secondary btn-sm">
        ← Back to Dashboard
      </button>

      <div className="flex items-start justify-between">
        <div>
          <h1>Incident {formatHash(inc.session_id, 12)}</h1>
          <p className="text-gray-600">{inc.mitre_stage || 'Unknown Stage'}</p>
        </div>
        <SeverityBadge severity={inc.severity} />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Narrative */}
          <div className="card">
            <h3 className="font-bold text-lg mb-3">📝 Narrative</h3>
            <p className="text-gray-700 leading-relaxed">
              {inc.narrative || 'No narrative available'}
            </p>
          </div>

          {/* Key Information */}
          <div className="card">
            <h3 className="font-bold text-lg mb-4">ℹ️  Information</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-gray-600">Created</p>
                <p className="font-mono text-xs">{formatDate(inc.created_at)}</p>
              </div>
              <div>
                <p className="text-gray-600">Confidence</p>
                <p className="font-bold">{(inc.confidence * 100).toFixed(0)}%</p>
              </div>
              <div>
                <p className="text-gray-600">Status</p>
                <p className="badge">{inc.status}</p>
              </div>
              <div>
                <p className="text-gray-600">MTTI</p>
                <p className="font-mono text-xs">{inc.mtti_seconds ? `${inc.mtti_seconds}s` : 'N/A'}</p>
              </div>
            </div>
          </div>

          {/* Graph Visualization */}
          <ProvGraph />

          {/* Edge Details */}
          <div className="card">
            <h3 className="font-bold text-lg mb-3">🔗 Event Chain ({incident.edges_count} edges)</h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {incident.edges?.map((edge) => (
                <div key={edge.id} className="bg-gray-50 p-3 rounded-lg text-xs">
                  <div className="font-mono text-gray-700 mb-1">
                    Node {edge.source_id} → <span className="text-red-600 font-bold">{edge.edge_type}</span> → Node {edge.target_id}
                  </div>
                  <p className="text-gray-500">{formatDate(edge.timestamp)}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Notes */}
          {inc.analyst_notes && (
            <div className="card border-l-4 border-warning bg-yellow-50">
              <p className="text-sm text-gray-700 font-semibold mb-1">Analyst Notes</p>
              <p className="text-sm text-gray-600">{inc.analyst_notes}</p>
            </div>
          )}
        </div>

        {/* Right Column: Actions */}
        <div className="space-y-6">
          <IncidentActions incident={inc} onUpdate={fetchIncident} />

          {/* Quick Info */}
          <div className="card">
            <h4 className="font-bold mb-3">📊 Quick Stats</h4>
            <div className="space-y-2 text-sm">
              <p><strong>Session ID:</strong> <span className="font-mono text-xs">{formatHash(inc.session_id)}</span></p>
              <p><strong>Nodes:</strong> {incident.nodes_count}</p>
              <p><strong>Edges:</strong> {incident.edges_count}</p>
              <p><strong>Severity:</strong> <SeverityBadge severity={inc.severity} /></p>
            </div>
          </div>

          {/* Resolution Info */}
          {inc.resolved_at && (
            <div className="card bg-green-50 border border-green-200">
              <p className="text-sm font-semibold text-green-800 mb-1">✅ Resolved</p>
              <p className="text-xs text-green-700">{formatDate(inc.resolved_at)}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}