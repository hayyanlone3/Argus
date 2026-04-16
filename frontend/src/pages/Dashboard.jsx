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
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-xl border border-slate-700/60 bg-slate-900 p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-slate-100 text-xl font-semibold tracking-wide">
              ARGUS • Dashboard
            </div>
            <div className="text-slate-400 text-sm font-mono">
              Provenance Graph Anomaly Detection • Live Monitoring
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-xs font-mono text-slate-400">
              {refreshing ? 'syncing…' : 'live'}
            </div>
            <div className={`h-2 w-2 rounded-full ${refreshing ? 'bg-yellow-400' : 'bg-green-400'}`} />
          </div>
        </div>

        {error && (
          <div className="mt-3 rounded-lg border border-red-500/40 bg-red-950/30 p-3 text-red-200 text-sm">
            {error}
          </div>
        )}
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {severityOrder.map((severity) => (
          <div key={severity} className="rounded-xl border border-slate-700/60 bg-slate-950 p-4">
            <div className="text-xs text-slate-400 font-mono">{severity}</div>
            <div className="text-3xl font-bold text-slate-100 mt-2">
              {num(normalized.sevDist?.[severity], 0)}
            </div>
            <div className="mt-2">
              <SeverityBadge severity={severity} />
            </div>
          </div>
        ))}
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-700/60 bg-slate-950 p-4">
          <div className="text-xs text-slate-400 font-mono">MODEL MATURITY</div>
          <div className="text-2xl font-bold text-slate-100 mt-2">
            {num(normalized.dataQuality, 0).toFixed(0)}%
          </div>
          <div className="text-xs text-slate-400 mt-1">Analyst feedback rate (weekly)</div>
        </div>

        <div className="rounded-xl border border-slate-700/60 bg-slate-950 p-4">
          <div className="text-xs text-slate-400 font-mono">FALSE POSITIVE RATE</div>
          <div className="text-2xl font-bold text-slate-100 mt-2">
            {num(normalized.fpRate, 0).toFixed(1)}%
          </div>
          <div className="text-xs text-slate-400 mt-1">Weekly metric</div>
        </div>

        <div className="rounded-xl border border-slate-700/60 bg-slate-950 p-4">
          <div className="text-xs text-slate-400 font-mono">OPEN INCIDENTS</div>
          <div className="text-2xl font-bold text-slate-100 mt-2">
            {num(normalized.statusDist?.OPEN, 0)}
          </div>
          <div className="text-xs text-slate-400 mt-1">Requires action</div>
        </div>
      </div>

      {/* Severity Filter */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setSelectedSeverity(null)}
          className={[
            "px-4 py-2 rounded-lg text-sm font-medium border",
            selectedSeverity === null
              ? "bg-slate-100 text-slate-900 border-slate-100"
              : "bg-slate-900 text-slate-200 border-slate-700/60 hover:bg-slate-800"
          ].join(" ")}
        >
          All Incidents
        </button>

        {severityOrder.map((sev) => (
          <button
            key={sev}
            onClick={() => setSelectedSeverity(sev)}
            className={[
              "px-4 py-2 rounded-lg text-sm font-medium border",
              selectedSeverity === sev
                ? "bg-slate-100 text-slate-900 border-slate-100"
                : "bg-slate-900 text-slate-200 border-slate-700/60 hover:bg-slate-800"
            ].join(" ")}
          >
            {sev}
          </button>
        ))}
      </div>

      {/* Incident Feed */}
      <div className="rounded-xl border border-slate-700/60 bg-slate-950 p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-slate-100 font-semibold">Incident Feed</div>
          <div className="text-xs text-slate-400 font-mono">
            {selectedSeverity ? `filter=${selectedSeverity}` : "filter=ALL"}
          </div>
        </div>
        <IncidentFeed severity={selectedSeverity} limit={20} />
      </div>

      {/* Tip */}
      <div className="rounded-xl border border-slate-700/60 bg-slate-900 p-4">
        <div className="text-slate-200 text-sm">
          <span className="font-semibold">Tip:</span> Click any incident card to view details, chain graph, and submit analyst feedback.
        </div>
      </div>
    </div>
  );
}