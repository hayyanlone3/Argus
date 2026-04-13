// src/components/incident/IncidentFeed.jsx
import React, { useEffect, useState } from 'react';
import IncidentCard from './IncidentCard';
import LoadingSpinner from '../common/LoadingSpinner';
import { incidentService } from '../../services/incidentService';

export default function IncidentFeed({ severity = null, limit = 20 }) {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchIncidents = async () => {
      try {
        setLoading(true);
        const data = await incidentService.getIncidents(severity, null, limit);
        setIncidents(data.incidents || []);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchIncidents();
    const interval = setInterval(fetchIncidents, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, [severity, limit]);

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="card border border-critical text-critical">Error: {error}</div>;
  if (!incidents.length) return <div className="card text-center text-gray-500">No incidents found</div>;

  return (
    <div className="grid grid-auto gap-4">
      {incidents.map((incident) => (
        <IncidentCard key={incident.session_id} incident={incident} />
      ))}
    </div>
  );
}