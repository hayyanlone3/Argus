// src/components/incident/IncidentFeed.jsx
import React, { useEffect, useState } from 'react';
import IncidentCard from './IncidentCard';
import LoadingSpinner from '../common/LoadingSpinner';
import { incidentService } from '../../services/incidentService';

export default function IncidentFeed({ severity = null, limit = 20 }) {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    const fetchIncidents = async (initial = false) => {
      try {
        if (initial) setLoading(true);
        else setRefreshing(true);

        const data = await incidentService.getIncidents(severity, null, limit);
        if (!mounted) return;

        setIncidents(data.incidents || []);
        setError(null);
      } catch (err) {
        if (!mounted) return;
        setError(err.message);
      } finally {
        if (!mounted) return;
        if (initial) setLoading(false);
        else setRefreshing(false);
      }
    };

    fetchIncidents(true);
    const interval = setInterval(() => fetchIncidents(false), 30000); // was 10s
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [severity, limit]);

  if (loading) return <LoadingSpinner />;
  
  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700 text-sm shadow-sm">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Syncing indicator */}
      <div className="flex justify-end">
        <div className="text-xs font-mono text-slate-500 flex items-center gap-2">
          {refreshing ? (
            <>
              syncing...
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-yellow-500"></span>
              </span>
            </>
          ) : (
            <>
              live
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </>
          )}
        </div>
      </div>

      {/* Feed Content */}
      {!incidents.length ? (
        <div className="rounded-xl border border-slate-200 bg-slate-50 py-8 text-center text-slate-500 text-sm shadow-sm">
          No incidents found
        </div>
      ) : (
        <div className="grid gap-4">
          {incidents.map((incident) => (
            <IncidentCard
              key={incident.session_id}
              incident={incident}
              // --- Add this: pass explicit source if needed ---
              source={incident.source}
            />
          ))}
        </div>
      )}
    </div>
  );
}