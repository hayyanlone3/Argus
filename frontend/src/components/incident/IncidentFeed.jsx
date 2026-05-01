// src/components/incident/IncidentFeed.jsx
import React, { useEffect, useState } from 'react';
import IncidentCard from './IncidentCard';
import LoadingSpinner from '../common/LoadingSpinner';
import { incidentService } from '../../services/incidentService';

export default function IncidentFeed({ severity = null, limit = 20, showMalwareToggle = true }) {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [statusFilter, setStatusFilter] = useState('NEW'); // Default to unhandled
  const [malwareOnly, setMalwareOnly] = useState(false);

  useEffect(() => {
    let mounted = true;

    const fetchIncidents = async (initial = false) => {
      try {
        if (initial) setLoading(true);
        else setRefreshing(true);

        const filter = statusFilter === 'ALL' ? null : statusFilter;
        const effectiveSeverity = malwareOnly ? 'CRITICAL' : severity;
        const data = await incidentService.getIncidents(effectiveSeverity, filter, limit);
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
    const interval = setInterval(() => fetchIncidents(false), 10000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [severity, limit, statusFilter, malwareOnly]);

  if (loading) return <LoadingSpinner />;
  
  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-700 text-sm shadow-sm">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Feed Controls */}
      <div className="flex justify-between items-center bg-[#0f172a] p-1 rounded-lg border border-slate-800">
        <div className="flex gap-1">
          {['NEW', 'ACKNOWLEDGED', 'ALL'].map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-4 py-1.5 text-[10px] font-black rounded transition-all ${statusFilter === s ? 'bg-slate-700 text-white' : 'text-slate-500 hover:text-slate-300'}`}
            >
              {s}
            </button>
          ))}
          {showMalwareToggle && (
            <button
              onClick={() => setMalwareOnly((prev) => !prev)}
              className={`px-4 py-1.5 text-[10px] font-black rounded transition-all ${malwareOnly ? 'bg-red-600 text-white' : 'text-slate-500 hover:text-slate-300'}`}
              title="Show CRITICAL malware incidents"
            >
              MALWARE
            </button>
          )}
        </div>
        
        <div className="text-xs font-mono text-slate-500 flex items-center gap-2 pr-2">
          {refreshing ? (
            <span className="flex items-center gap-2">syncing <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-pulse" /></span>
          ) : (
            <span className="flex items-center gap-2">live <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /></span>
          )}
        </div>
      </div>

      {/* Feed Content */}
      {!incidents.length ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/50 py-12 text-center text-slate-500 text-xs italic shadow-sm">
          No {statusFilter.toLowerCase()} incidents found
        </div>
      ) : (
        <div className="grid gap-4">
          {incidents.map((incident) => (
            <IncidentCard
              key={incident.session_id}
              incident={incident}
            />
          ))}
        </div>
      )}
    </div>
  );
}
