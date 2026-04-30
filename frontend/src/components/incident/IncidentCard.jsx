// src/components/incident/IncidentCard.jsx
import React from 'react';
import { Link } from 'react-router-dom';
import SeverityBadge from '../common/SeverityBadge';
import { formatDate, formatHash } from '../../utils/formatters';
import { getSeverityBgClass } from '../../utils/helpers';

export default function IncidentCard({ incident }) {
  if (!incident) return null;

  const chainSummary = incident.process_chain?.length > 0
    ? incident.process_chain.map(c => `${c.parent} \u2192 ${c.child}`).slice(0, 3).join(', ')
    : null;

  const maxScore = incident.max_edge_score ?? incident.confidence ?? 0;

  return (
    <Link to={`/incident/${incident.session_id}`}>
      <div className={`card cursor-pointer transform hover:scale-105 transition-transform ${getSeverityBgClass(incident.severity)}`}>
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <div className="flex items-center">
              <h3 className="font-bold text-lg text-gray-900 mb-1">
                Incident {formatHash(incident.session_id, 8)}
              </h3>
              {incident.source === 'sysmon_autoscan' && (
                <span
                  className="ml-2 px-2 py-0.5 bg-red-500 text-white text-xs rounded-full font-bold uppercase tracking-wide"
                  title="Automatically scanned by Layer 0 (Sysmon)"
                >
                  AutoScan
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600">{incident.mitre_stage || 'Unknown Stage'}</p>
          </div>
          <SeverityBadge severity={incident.severity} />
        </div>

        {chainSummary && (
          <div className="mb-3 p-2 rounded bg-white/60 border border-gray-200">
            <p className="text-xs text-gray-500 mb-1">Process Chain</p>
            <p className="font-mono text-xs text-gray-800">{chainSummary}</p>
          </div>
        )}

        <div className="grid grid-cols-3 gap-3 mb-4 text-sm">
          <div>
            <p className="text-gray-600">Created</p>
            <p className="font-mono text-xs">{formatDate(incident.created_at)}</p>
          </div>
          <div>
            <p className="text-gray-600">Max Score</p>
            <p className="font-bold">{(maxScore * 100).toFixed(0)}%</p>
          </div>
          <div>
            <p className="text-gray-600">Events</p>
            <p className="font-bold">{incident.edge_count || 0}</p>
          </div>
        </div>

        {incident.narrative && (
          <p className="text-sm text-gray-700 mb-3 line-clamp-3">
            {incident.narrative}
          </p>
        )}

        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>Status: <span className="font-semibold">{incident.status}</span></span>
          <span>{incident.edge_count || 0} event(s)</span>
        </div>
      </div>
    </Link>
  );
}
