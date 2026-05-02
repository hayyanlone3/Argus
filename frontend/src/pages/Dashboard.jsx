import React, { useEffect, useMemo, useState } from 'react';
import IncidentFeed from '../components/incident/IncidentFeed';
import { incidentService } from '../services/incidentService';
import { learningService } from '../services/learningService';
import LoadingSpinner from '../components/common/LoadingSpinner';
import SeverityBadge from '../components/common/SeverityBadge';

const severityOrder = ['CRITICAL', 'WARNING', 'UNKNOWN', 'BENIGN'];

function num(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [learningStats, setLearningStats] = useState(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [error, setError] = useState(null);
  const [selectedSeverity, setSelectedSeverity] = useState(null);

  const normalized = useMemo(() => {
    // Be defensive: accept multiple backend shapes
    const sevDist =
      stats?.severity_distribution ||
      stats?.severity_dist ||
      stats?.distribution?.severity ||
      {};

    const statusDist =
      stats?.status_distribution ||
      stats?.status_dist ||
      stats?.distribution?.status ||
      {};

    const weekly =
      learningStats?.weekly_stats ||
      learningStats?.weekly ||
      learningStats?.stats?.weekly_stats ||
      {};

    const dataQuality =
      weekly?.data_quality_percent ??
      weekly?.data_quality ??
      weekly?.data_quality_rate ??
      0;

    const fpRate =
      weekly?.fp_rate_percent ??
      weekly?.false_positive_rate_percent ??
      weekly?.fp_rate ??
      0;

    return {
      sevDist,
      statusDist,
      dataQuality,
      fpRate,
    };
  }, [stats, learningStats]);

  const fetchStats = async (initial = false) => {
    try {
      if (initial) setLoading(true);
      else setRefreshing(true);

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
      if (initial) setLoading(false);
      else setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStats(true);
    const interval = setInterval(() => fetchStats(false), 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) return <LoadingSpinner />;

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-10">
      {/* Header */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
              ARGUS <span className="text-slate-300 mx-2"></span> Dashboard
            </h1>
            <p className="text-slate-500 text-sm md:text-base font-medium mt-1">
              Provenance Graph Anomaly Detection Live Monitoring
            </p>
          </div>

          <div className="flex items-center gap-3 bg-slate-50 px-4 py-2 rounded-full border border-slate-200/60 shadow-inner">
            <span className="text-xs font-bold tracking-wider text-slate-600 uppercase">
              {refreshing ? 'Syncing...' : 'Live System'}
            </span>
            <span className="relative flex h-3 w-3">
              {refreshing && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75"></span>}
              <span className={`relative inline-flex rounded-full h-3 w-3 ${refreshing ? 'bg-yellow-500' : 'bg-emerald-500'}`}></span>
            </span>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 flex items-center gap-3 text-red-800 text-sm font-medium shadow-sm">
            <span className="text-red-500 text-lg"> </span>
            {error}
          </div>
        )}
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        {severityOrder.map((severity) => (
          <div 
            key={severity} 
            className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow duration-200 flex flex-col justify-between ${
              severity === 'CRITICAL' ? 'border-l-4 border-l-red-500' :
              severity === 'WARNING' ? 'border-l-4 border-l-amber-500' :
              severity === 'UNKNOWN' ? 'border-l-4 border-l-slate-400' :
              severity === 'BENIGN' ? 'border-l-4 border-l-emerald-500' : ''
            }`}
          >
            <div className="text-xs font-bold text-slate-500 tracking-wider uppercase mb-3">
              {severity}
            </div>
            <div className="flex items-end justify-between">
              <div className="text-4xl font-extrabold text-slate-900 tracking-tight">
                {num(normalized.sevDist?.[severity], 0)}
              </div>
              <div className="mb-1">
                <SeverityBadge severity={severity} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="rounded-2xl border border-slate-200 bg-linear-to-br from-white to-slate-50 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-indigo-500" viewBox="0 0 20 20" fill="currentColor">
              <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
            </svg>
            <div className="text-xs font-bold text-slate-500 tracking-wider uppercase">Model Maturity</div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 mt-1">
            {num(normalized.dataQuality, 0).toFixed(0)}%
          </div>
          <div className="text-sm font-medium text-slate-500 mt-2">Analyst feedback rate (weekly)</div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-linear-to-br from-white to-slate-50 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-rose-500" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clipRule="evenodd" />
            </svg>
            <div className="text-xs font-bold text-slate-500 tracking-wider uppercase">False Positive Rate</div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 mt-1">
            {num(normalized.fpRate, 0).toFixed(1)}%
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-linear-to-br from-white to-slate-50 p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-amber-500" viewBox="0 0 20 20" fill="currentColor">
              <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
              <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
            </svg>
            <div className="text-xs font-bold text-slate-500 tracking-wider uppercase">Open Incidents</div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 mt-1">
            {num(normalized.statusDist?.OPEN, 0)}
          </div>
          <div className="text-sm font-medium text-slate-500 mt-2">Requires immediate action</div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-md overflow-hidden">
        {/* Feed Header & Filters */}
        <div className="border-b border-slate-100 bg-slate-50/50 p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <h2 className="text-xl font-bold text-slate-900">Incident Feed</h2>
            <div className="bg-white rounded-md px-3 py-1.5 text-xs font-bold text-slate-600 tracking-wider border border-slate-200 shadow-sm uppercase">
              {selectedSeverity ? `Filtered by: ${selectedSeverity}` : "Showing All Incidents"}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedSeverity(null)}
              className={[
                "px-5 py-2.5 rounded-lg text-sm font-bold border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2",
                selectedSeverity === null
                  ? "bg-blue-600 text-white border-blue-600 shadow-md focus:ring-blue-600"
                  : "bg-white text-slate-600 border-slate-300 hover:bg-slate-100 hover:text-slate-900 hover:border-slate-400 shadow-sm"
              ].join(" ")}
            >
              All Incidents
            </button>

            {severityOrder.map((sev) => (
              <button
                key={sev}
                onClick={() => setSelectedSeverity(sev)}
                className={[
                  "px-5 py-2.5 rounded-lg text-sm font-bold border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2",
                  selectedSeverity === sev
                    ? "bg-blue-600 text-white border-blue-600 shadow-md focus:ring-blue-600"
                    : "bg-white text-slate-600 border-slate-300 hover:bg-slate-100 hover:text-slate-900 hover:border-slate-400 shadow-sm"
                ].join(" ")}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        {/* Feed Content */}
        <div className="p-6 bg-white">
          <IncidentFeed severity={selectedSeverity} limit={20} showMalwareToggle={false} />
        </div>
      </div>
      <div className="flex items-start gap-4 rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5 shadow-sm">
        <div className="text-indigo-900 text-sm font-medium pt-1">
          <span className="font-extrabold tracking-wide uppercase text-xs text-indigo-600 bg-indigo-100/50 px-2 py-1 rounded mr-3 border border-indigo-200/50">Pro Tip</span>
          Click any incident card above to view its deep-dive details, interactive event chain graph, and submit analyst feedback.
        </div>
      </div>
    </div>
  );
}