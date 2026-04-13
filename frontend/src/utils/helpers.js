// src/utils/helpers.js
import { SEVERITY_COLORS } from '../config/constants';

export const getSeverityColor = (severity) => {
  return SEVERITY_COLORS[severity] || '#999';
};

export const getSeverityBgClass = (severity) => {
  const mapping = {
    CRITICAL: 'bg-red-50',
    WARNING: 'bg-yellow-50',
    UNKNOWN: 'bg-blue-50',
    BENIGN: 'bg-green-50',
  };
  return mapping[severity] || 'bg-gray-50';
};

export const getSeverityBadgeClass = (severity) => {
  const mapping = {
    CRITICAL: 'badge-critical',
    WARNING: 'badge-warning',
    UNKNOWN: 'badge-unknown',
    BENIGN: 'badge-benign',
  };
  return mapping[severity] || '';
};

export const getLayerColor = (layer) => {
  const colors = {
    0: '#6f42c1',
    1: '#0dcaf0',
    2: '#fd7e14',
    3: '#0d6efd',
    4: '#198754',
    5: '#6c757d',
  };
  return colors[layer] || '#999';
};

export const getLayerName = (layer) => {
  const names = {
    0: 'Bouncer',
    1: 'Graph Engine',
    2: 'Scoring',
    3: 'Correlator',
    4: 'Response',
    5: 'Learning',
  };
  return names[layer] || 'Unknown';
};

export const getTruncatedPath = (path, maxLength = 40) => {
  if (!path || path.length <= maxLength) return path;
  const start = path.substring(0, 15);
  const end = path.substring(path.length - 15);
  return `${start}...${end}`;
};

export const isHighRisk = (severity) => {
  return severity === 'CRITICAL' || severity === 'WARNING';
};

export const sortIncidentsBySeverity = (incidents) => {
  const severityOrder = { CRITICAL: 0, WARNING: 1, UNKNOWN: 2, BENIGN: 3 };
  return [...incidents].sort((a, b) => {
    return (severityOrder[a.severity] || 99) - (severityOrder[b.severity] || 99);
  });
};