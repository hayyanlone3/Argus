import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { incidentService } from '../services/incidentService';
import D3ProvenanceGraph from '../components/graph/D3ProvenanceGraph';
import LoadingSpinner from '../components/common/LoadingSpinner';
import SeverityBadge from '../components/common/SeverityBadge';
import IncidentActions from '../components/incident/IncidentActions';
import { formatDate } from '../utils/formatters';

export default function IncidentDetail() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [incidentData, setIncidentData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('graph');

  const fetchIncident = () => {
    incidentService.getIncident(sessionId)
      .then(setIncidentData)
      .catch(err => console.error("Fetch Error:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchIncident();
    const interval = setInterval(fetchIncident, 10000);
    return () => clearInterval(interval);
  }, [sessionId]);

  


  if (loading) return <LoadingSpinner />;
  if (!incidentData || !incidentData.incident) return (
    <div className="min-h-screen bg-linear-to-br from-slate-50 via-white to-slate-100 p-10">
      <div className="max-w-3xl mx-auto rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <button onClick={() => navigate(-1)} className="text-slate-600 hover:text-slate-900 mb-6">← Back to incidents</button>
        <div className="text-red-600 font-black text-2xl uppercase">Incident telemetry missing</div>
        <p className="text-slate-500 mt-2 text-sm">The system could not load this case. Try refreshing or pick another incident.</p>
      </div>
    </div>
  );

  const inc = incidentData.incident;
  const scoreTone = (inc.confidence || 0) > 0.8 ? 'bg-red-50 text-red-700 border-red-200' : 'bg-amber-50 text-amber-700 border-amber-200';

  const getEdgeTypeValue = (edge) => {
    if (!edge?.edge_type) return '';
    if (typeof edge.edge_type === 'string') return edge.edge_type;
    if (edge.edge_type?.value) return edge.edge_type.value;
    return String(edge.edge_type);
  };

  const shortName = (node) => {
    if (!node) return 'unknown process';
    if (node.name) return node.name;
    if (node.path) return node.path.split(/[\\/]/).pop();
    return 'unknown process';
  };

  const edgeVerb = (edgeType) => {
    const normalized = (edgeType || '').toUpperCase();
    const verbs = {
      SPAWNED: 'spawned',
      EXECUTED_SCRIPT: 'executed a script via',
      INJECTED_INTO: 'injected into',
      SUBSCRIBED_WMI: 'subscribed to WMI via',
      MODIFIED_REG: 'modified the registry using',
      READ: 'read from',
      WROTE: 'wrote to',
      CREATED: 'created',
      CONNECTED: 'connected to',
    };
    return verbs[normalized] || 'interacted with';
  };

  const edgesForIncident = (incidentData.edges || []).filter(e => {
    try {
      if (!e) return false;
      if (e.session_id && inc.session_id) return String(e.session_id) === String(inc.session_id);
      if (e.session_id && sessionId) return String(e.session_id) === String(sessionId);
      return true;
    } catch { return true; }
  });

  const formatShortNarrative = (text) => {
    if (!text) return '';
    const cleaned = text.replace(/[A-Za-z]:(\\|\/)[^\s]*/g, '')
                        .replace(/\b[0-9a-f]{8,}\b/gi, '')
                        .replace(/\s+/g, ' ').trim();
    const parts = cleaned.split(/(?<=[.!?])\s+/);
    return parts.slice(0, 2).join(' ');
  };

  const transformNarrative = (text) => {
    if (!text) return '';
    const lines = String(text).split(/\r?\n/).map(l => l.trim()).filter(Boolean);
    const verbs = {
      FILE_CREATE: 'created file',
      FILE_MODIFY: 'modified file',
      PROCESS_CREATE: 'launched process',
      PROCESS_TERMINATE: 'terminated process',
      REGKEY_CREATE: 'created registry key',
      NETWORK_CONNECT: 'connected to network endpoint',
      SERVICE_CREATE: 'created service',
      DLL_LOAD: 'loaded library',
      DEFAULT: 'performed action'
    };

    const parseLine = (line) => {
      const m = line.match(/^([A-Z0-9_]+):\s*(.+)$/i);
      if (m) {
        const key = m[1].toUpperCase();
        const raw = m[2].trim();
        const name = (raw.split(/[\\/\s]/).filter(Boolean).pop() || raw).replace(/^\.*|\.*$/g, '');
        const verb = verbs[key] || verbs.DEFAULT;
        return `${verb.charAt(0).toUpperCase() + verb.slice(1)} ${name}.`;
      }
      return formatShortNarrative(line);
    };

    if (lines.length === 1) return parseLine(lines[0]);
    return lines.map(parseLine).slice(0, 2).join(' ');
  };

  const nodesForIncident = (incidentData.nodes || []).filter(n => {
    return edgesForIncident.some(e => e.source_id === n.id || e.target_id === n.id);
  });

  const buildNarrative = () => {
    const edges = [...edgesForIncident]
      .sort((a, b) => new Date(a.timestamp || 0) - new Date(b.timestamp || 0))
      .slice(0, 4);
    if (!edges.length) return '';

    const nodesById = new Map((incidentData.nodes || []).map(n => [n.id, n]));
    const sentences = edges.map((edge) => {
      const src = nodesById.get(edge.source_id);
      const tgt = nodesById.get(edge.target_id);
      const verb = edgeVerb(getEdgeTypeValue(edge));
      return `${shortName(src)} ${verb} ${shortName(tgt)}.`;
    });

    const remaining = edgesForIncident.length - edges.length;
    if (remaining > 0) sentences.push(`The chain continued with ${remaining} more actions.`);

    return sentences.join(' ');
  };

  const getNodeScore = (node) => {
    const direct = Number(node?.anomaly_score || 0);
    if (direct > 0) return direct;

    const edges = incidentData.edges || [];
    let maxScore = 0;
    for (const edge of edges) {
      if (edge.source_id !== node.id && edge.target_id !== node.id) continue;
      const score = Math.max(Number(edge.anomaly_score || 0), Number(edge.ml_anomaly_score || 0));
      if (score > maxScore) maxScore = score;
    }
    return maxScore;
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-slate-50 via-white to-slate-100 text-slate-900">
      {/* Header */}
      <div className="border-b border-slate-200 bg-white/80 backdrop-blur-lg">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-4">
              <button onClick={() => navigate(-1)} className="p-2 rounded-full border border-slate-200 hover:bg-slate-100 transition-colors">
                <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
              </button>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`text-[11px] font-black uppercase px-2.5 py-1 rounded-full border ${scoreTone}`}>
                    Confidence {Math.round((inc.confidence || 0) * 100)}%
                  </span>
                  <span className="text-[11px] font-bold uppercase px-2.5 py-1 rounded-full border border-slate-200 bg-slate-50 text-slate-600">
                    Status {inc.status || 'OPEN'}
                  </span>
                </div>
                <h1 className="text-2xl font-black tracking-tight text-slate-900 mt-2">
                  Incident {sessionId.substring(0, 16)}
                </h1>
                <p className="text-sm text-slate-500 mt-1">Created {formatDate(inc.created_at)}</p>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
                <div className="text-[10px] uppercase font-black text-slate-500">Severity</div>
                <div className="mt-1"><SeverityBadge severity={inc.severity} /></div>
              </div>
              </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-12 gap-6 px-6 py-6">
        {/* Forensic Sidebar */}
        <div className="col-span-12 xl:col-span-4 space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <IncidentActions incident={inc} onUpdate={fetchIncident} />
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
           <section>
              <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-500 mb-3">Attack Narrative</h3>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700 leading-relaxed">
                {transformNarrative(inc.narrative) || buildNarrative() || 'Analyzing telemetry for behavioral markers...'}
              </div>
            </section>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <section>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-500">Process Chain</h3>
                <span className="text-[10px] font-bold text-slate-400">{incidentData.edges_count || 0} events</span>
              </div>
              <div className="space-y-3">
                {edgesForIncident.slice().sort((a, b) => new Date(a.timestamp || 0) - new Date(b.timestamp || 0)).map((edge, i) => {
                  const srcNode = (incidentData.nodes || []).find(n => n.id === edge.source_id);
                  const tgtNode = (incidentData.nodes || []).find(n => n.id === edge.target_id);
                  const edgeType = getEdgeTypeValue(edge);
                  return (
                    <div key={i} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
                      <div className="flex items-center justify-between">
                        <div className="text-xs font-semibold text-slate-800">
                          {srcNode?.name || 'unknown'} → {tgtNode?.name || 'unknown'}
                        </div>
                        {edge.final_severity && (
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                            edge.final_severity === 'CRITICAL'
                              ? 'border-red-200 bg-red-50 text-red-700'
                              : edge.final_severity === 'WARNING'
                              ? 'border-amber-200 bg-amber-50 text-amber-700'
                              : 'border-slate-200 bg-slate-50 text-slate-600'
                          }`}>{edge.final_severity}</span>
                        )}
                      </div>
                      {srcNode?.path && <div className="text-[11px] text-slate-500 mt-1 truncate">{srcNode.path}</div>}
                      {tgtNode?.path && <div className="text-[11px] text-slate-500 truncate">{tgtNode.path}</div>}
                      <div className="mt-2 flex items-center justify-between text-[10px] text-slate-500">
                        <span>{edgeType?.toUpperCase() || 'UNKNOWN'}</span>
                        <span className="font-mono">score {Math.max(Number(edge.anomaly_score || 0), Number(edge.ml_anomaly_score || 0)).toFixed(2)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <section>
              <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-500 mb-3">MITRE ATT&CK</h3>
              {inc.mitre_stage ? (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-800">
                  {inc.mitre_stage.toUpperCase()}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">Detecting tactical signatures...</p>
              )}
            </section>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <section>
              <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-500 mb-3">Activity Timeline</h3>
              <div className="space-y-4">
                {edgesForIncident.slice().sort((a, b) => new Date(a.timestamp || 0) - new Date(b.timestamp || 0)).slice(0, 5).map((edge, i) => {
                  const srcNode = (incidentData.nodes || []).find(n => n.id === edge.source_id);
                  const tgtNode = (incidentData.nodes || []).find(n => n.id === edge.target_id);
                  return (
                    <div key={i} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <div className="text-[10px] text-slate-400 font-mono">{formatDate(edge.timestamp)}</div>
                      <div className="text-xs font-bold text-slate-800 mt-1">{getEdgeTypeValue(edge)?.toUpperCase() || 'ACTION'}</div>
                      <div className="text-[11px] text-slate-500 truncate">{srcNode?.name || 'unknown'} → {tgtNode?.name || 'unknown'}</div>
                    </div>
                  );
                })}
              </div>
            </section>
          </div>
        </div>

        {/* Main Panel */}
        <div className="col-span-12 xl:col-span-8 flex flex-col gap-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setActiveTab('graph')}
                className={`px-4 py-2 text-xs font-black uppercase rounded-full border transition-all ${
                  activeTab === 'graph'
                    ? 'border-slate-900 bg-slate-900 text-white'
                    : 'border-slate-200 text-slate-600 hover:border-slate-300'
                }`}
              >
                Provenance Graph
              </button>
              <button
                onClick={() => setActiveTab('evidence')}
                className={`px-4 py-2 text-xs font-black uppercase rounded-full border transition-all ${
                  activeTab === 'evidence'
                    ? 'border-slate-900 bg-slate-900 text-white'
                    : 'border-slate-200 text-slate-600 hover:border-slate-300'
                }`}
              >
                Evidence
              </button>
            </div>
          </div>

          <div className="flex-1 rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
            {activeTab === 'graph' ? (
              <div className="h-full">
                <D3ProvenanceGraph
                  nodes={nodesForIncident}
                  edges={edgesForIncident}
                />
              </div>
            ) : (
              <div className="p-6 h-full overflow-y-auto">
                <h2 className="text-xs font-black uppercase tracking-widest text-slate-500 mb-4">Forensic Artifacts</h2>
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 font-black">
                      <th className="pb-3 uppercase">Node Identifier</th>
                      <th className="pb-3 uppercase text-center">Type</th>
                      <th className="pb-3 uppercase text-right">Anomaly Score</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {(incidentData.nodes || [])
                      .map(n => ({ node: n, score: getNodeScore(n) }))
                      .sort((a, b) => b.score - a.score)
                      .map(({ node: n, score }) => (
                        <tr key={n.id} className="hover:bg-slate-50 transition-colors">
                          <td className="py-3 font-mono text-slate-600 truncate">{n.path || n.name || n.id}</td>
                          <td className="py-3 text-center font-bold uppercase text-slate-500">{n.type}</td>
                          <td className="py-3 text-right font-mono text-rose-600">
                            {score > 0 ? score.toFixed(4) : '—'}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}