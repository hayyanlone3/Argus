// src/pages/Layer1Dashboard.jsx
import React, { useEffect, useState } from 'react';
import ProvGraph from '../components/graph/ProvGraph';
import { graphService } from '../services/graphService';
import LoadingSpinner from '../components/common/LoadingSpinner';

export default function Layer1Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    const fetchStats = async (initial = false) => {
      try {
        if (initial) setLoading(true);
        const data = await graphService.getStats();
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
    const interval = setInterval(() => fetchStats(false), 20000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 shadow-sm border border-emerald-200">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
                Layer 1 <span className="text-slate-300 mx-2"></span> Graph Engine
              </h1>
            </div>
            <p className="text-slate-500 text-sm md:text-base font-medium ml-11">
              Provenance graph construction and event correlation
            </p>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 flex items-center gap-3 text-red-800 text-sm font-medium shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-red-600" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {error}
          </div>
        )}
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow duration-200">
            <div className="text-xs font-bold text-slate-500 tracking-wider uppercase mb-3">Total Nodes</div>
            <div className="text-4xl font-extrabold text-slate-900 tracking-tight">{stats.total_nodes || 0}</div>
          </div>
          
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow duration-200">
            <div className="text-xs font-bold text-slate-500 tracking-wider uppercase mb-3">Total Edges</div>
            <div className="text-4xl font-extrabold text-slate-900 tracking-tight">{stats.total_edges || 0}</div>
          </div>
          
          <div className="rounded-2xl border border-slate-200 border-l-4 border-l-rose-500 bg-white p-5 shadow-sm hover:shadow-md transition-shadow duration-200">
            <div className="text-xs font-bold text-slate-500 tracking-wider uppercase mb-3">Active (24h)</div>
            <div className="text-4xl font-extrabold text-rose-600 tracking-tight">{stats.active_edges_24h || 0}</div>
          </div>
          
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow duration-200">
            <div className="text-xs font-bold text-slate-500 tracking-wider uppercase mb-3">Window</div>
            <div className="text-4xl font-extrabold text-slate-900 tracking-tight">24h</div>
          </div>
        </div>
      )}

      {/* Node Types */}
      {stats?.node_breakdown && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-bold text-slate-900 mb-5">Node Types</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
            {Object.entries(stats.node_breakdown).map(([type, count]) => (
              <div key={type} className="rounded-xl border border-slate-100 bg-slate-50 p-4 flex flex-col items-center justify-center shadow-sm hover:bg-slate-100 transition-colors">
                <div className="text-2xl font-bold text-slate-800">{count}</div>
                <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mt-1 text-center">{type}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Edge Types */}
      {stats?.edge_breakdown && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-bold text-slate-900 mb-5">Edge Types</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(stats.edge_breakdown).map(([type, count]) => (
              <div key={type} className="rounded-xl border border-slate-100 bg-slate-50 p-4 flex flex-col items-center justify-center shadow-sm hover:bg-slate-100 transition-colors">
                <div className="text-2xl font-bold text-indigo-600">{count}</div>
                <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mt-1 text-center">{type}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Graph Visualization */}
      <ProvGraph />
        </div>
  );
}