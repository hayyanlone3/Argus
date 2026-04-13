// src/components/incident/IncidentCard.jsx
import React from 'react';
import { Link } from 'react-router-dom';
import SeverityBadge from '../common/SeverityBadge';
import { formatDate, formatHash } from '../../utils/formatters';
import { getSeverityBgClass } from '../../utils/helpers';

export default function IncidentCard({ incident }) {
  if (!incident) return null;

  return (
    <Link to={`/incident/${incident.session_id}`}>
      <div className={`card cursor-pointer transform hover:scale-105 transition-transform ${getSeverityBgClass(incident.severity)}`}>
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="font-bold text-lg text-gray-900 mb-1">
              Incident {formatHash(incident.session_id, 8)}
            </h3>
            <p className="text-sm text-gray-600">{incident.mitre_stage || 'Unknown Stage'}</p>
          </div>
          <SeverityBadge severity={incident.severity} />
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
          <div>
            <p className="text-gray-600">Created</p>
            <p className="font-mono text-xs">{formatDate(incident.created_at)}</p>
          </div>
          <div>
            <p className="text-gray-600">Confidence</p>
            <p className="font-bold">{(incident.confidence * 100).toFixed(0)}%</p>
          </div>
        </div>

        {incident.narrative && (
          <p className="text-sm text-gray-700 mb-3 line-clamp-3">
            {incident.narrative}
          </p>
        )}

        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>Status: <span className="font-semibold">{incident.status}</span></span>
          <span>→</span>
        </div>
      </div>
    </Link>
  );
}