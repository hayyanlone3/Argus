import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { incidentService } from '../services/incidentService';
import D3ProvenanceGraph from '../components/graph/D3ProvenanceGraph';
import LoadingSpinner from '../components/common/LoadingSpinner';
import SeverityBadge from '../components/common/SeverityBadge';
import { formatDate } from '../utils/formatters';

export default function IncidentDetail() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [incidentData, setIncidentData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('graph');
  const [acting, setActing] = useState(false);

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

  const handleAcknowledge = async () => {
    try {
      setActing(true);
      await incidentService.updateStatus(sessionId, 'ACKNOWLEDGED');
      fetchIncident();
      alert("✅ Incident Acknowledged");
    } catch (err) {
      alert("❌ Failed to acknowledge: " + err.message);
    } finally {
      setActing(false);
    }
  };

  const handleTerminate = async () => {
    // Prefer PID from sysmon-backed edge metadata (Node.id is NOT an OS PID)
    const pid =
      (incidentData.edges || [])
        .map(e => e?.edge_metadata?.child_pid || e?.edge_metadata?.parent_pid)
        .find(v => v && String(v).match(/^\d+$/)) || null;

    if (!pid) {
      alert("⚠️ No traceable process ID found for termination.");
      return;
    }

    if (!window.confirm(`Force terminate PID ${pid}?`)) return;

    try {
      setActing(true);
      await incidentService.terminateProcess(pid);
      alert(`✅ PID ${pid} Terminated.`);
      fetchIncident();
    } catch (err) {
       alert("❌ Termination failed: " + err.message);
    } finally {
       setActing(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (!incidentData || !incidentData.incident) return (
    <div className="bg-[#0f172a] min-h-screen p-20 text-center">
       <button onClick={() => navigate(-1)} className="text-slate-400 hover:text-white mb-8">← RETURN TO BASE</button>
       <div className="text-red-500 font-black text-2xl uppercase">Case Error: Incident Telemetry Missing</div>
    </div>
  );

  const inc = incidentData.incident;
  const scoreColor = (inc.confidence || 0) > 0.8 ? 'text-red-500' : 'text-amber-500';

  return (
    <div className="min-h-screen bg-[#020617] text-slate-200 font-sans">
      {/* Premium Header */}
      <div className="border-b border-slate-800 bg-[#0f172a]/80 backdrop-blur-xl p-6 sticky top-0 z-20 flex justify-between items-center">
        <div className="flex items-center gap-6">
          <button onClick={() => navigate(-1)} className="p-2 hover:bg-slate-800 rounded-full transition-colors">
            <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          </button>
          <div>
            <div className="flex items-center gap-3">
              <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded border border-slate-700 bg-slate-900 ${scoreColor}`}>
                CONFIDENCE: {Math.round((inc.confidence || 0) * 100)}%
              </span>
              <h1 className="text-lg font-black tracking-tight text-white uppercase">CASE ID: {sessionId.substring(0, 16)}</h1>
            </div>
            <p className="text-[10px] text-slate-500 font-mono mt-1">MTTI: {inc.mtti_seconds || '0'}s | CREATED: {formatDate(inc.created_at)}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <div className="flex flex-col items-end mr-4">
            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Severity</span>
            <SeverityBadge severity={inc.severity} />
          </div>
          <button 
            disabled={acting || inc.status === 'ACKNOWLEDGED'}
            onClick={handleAcknowledge}
            className="px-6 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 rounded text-xs font-black transition-all border border-slate-700"
          >
            {inc.status === 'ACKNOWLEDGED' ? 'ACKNOWLEDGED' : 'ACKNOWLEDGE'}
          </button>
          <button 
            disabled={acting}
            onClick={handleTerminate}
            className="px-6 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white rounded text-xs font-black shadow-lg shadow-red-900/20 transition-all"
          >
            {acting ? 'EXECUTING...' : 'TERMINATE THREAT'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 h-[calc(100vh-92px)]">
        {/* Forensic Intel Sidebar */}
        <div className="col-span-3 border-r border-slate-800 bg-[#0f172a] p-6 overflow-y-auto space-y-8">
           <section>
              <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                Attack Narrative
              </h3>
              <div className="bg-slate-900/50 rounded p-4 border border-slate-800/80 italic text-slate-300 text-sm leading-relaxed">
                "{inc.narrative || 'Analyzing telemetry for behavioral markers...'}"
              </div>
           </section>

           <section>
              <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                MITRE ATT&CK Mapping
              </h3>
              <div className="space-y-2">
                 {inc.mitre_stage ? (
                    <div className="bg-red-900/10 text-red-400 p-2 rounded border border-red-900/20 text-xs font-bold flex justify-between">
                       <span>{inc.mitre_stage.toUpperCase()}</span>
                       <span className="opacity-50">T1547</span>
                    </div>
                 ) : (
                    <p className="text-slate-600 text-xs italic">Detecting tactical signatures...</p>
                 )}
              </div>
           </section>

           <section>
              <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                Activity Timeline
              </h3>
              <div className="relative pl-6 border-l border-slate-800 space-y-6 text-xs">
                 {(incidentData.edges || []).slice(0, 5).map((edge, i) => (
                    <div key={i} className="relative">
                       <span className="absolute -left-[30px] top-1 w-2 h-2 rounded-full bg-slate-700 border border-slate-950" />
                       <p className="text-slate-500 font-mono">{formatDate(edge.timestamp)}</p>
                       <p className="font-black text-white">{edge.edge_type?.toUpperCase() || 'ACTION'}</p>
                       <p className="text-slate-400 truncate opacity-60 italic">{String(edge.source_id).substring(0,8)} {" -> "} {String(edge.target_id).substring(0,8)}</p>
                    </div>
                 ))}
              </div>
           </section>
        </div>

        {/* Tactical View Center */}
        <div className="col-span-9 relative flex flex-col">
           <div className="absolute top-6 left-6 z-10 flex p-1 bg-slate-900/80 backdrop-blur rounded border border-slate-800 shadow-2xl">
              <button 
                onClick={() => setActiveTab('graph')}
                className={`px-6 py-1.5 text-[10px] font-black rounded transition-all ${activeTab === 'graph' ? 'bg-slate-700 text-white shadow-inner' : 'text-slate-500 hover:text-slate-300'}`}
              >
                PROVENANCE GRAPH
              </button>
              <button 
                onClick={() => setActiveTab('evidence')}
                className={`px-6 py-1.5 text-[10px] font-black rounded transition-all ${activeTab === 'evidence' ? 'bg-slate-700 text-white shadow-inner' : 'text-slate-500 hover:text-slate-300'}`}
              >
                EVIDENCE
              </button>
           </div>

           <div className="flex-grow">
              {activeTab === 'graph' ? (
                 <D3ProvenanceGraph 
                    nodes={incidentData.nodes || []} 
                    edges={incidentData.edges || []} 
                 />
              ) : (
                 <div className="p-10 h-full overflow-y-auto">
                    <h2 className="text-xs font-black text-slate-500 uppercase tracking-widest mb-8">Forensic Artifacts</h2>
                    <table className="w-full text-left text-xs border-collapse">
                       <thead>
                          <tr className="border-b border-slate-800 text-slate-500 font-black">
                            <th className="pb-4 uppercase">Node Identifier</th>
                            <th className="pb-4 uppercase text-center">Type</th>
                            <th className="pb-4 uppercase text-right">Anomaly Score</th>
                          </tr>
                       </thead>
                       <tbody className="divide-y divide-slate-800/50">
                          {(incidentData.nodes || []).map(n => (
                            <tr key={n.id} className="hover:bg-slate-800/20 transition-colors group">
                               <td className="py-4 font-mono text-slate-400 group-hover:text-blue-400 transition-colors">{n.path || n.name || n.id}</td>
                               <td className="py-4 text-center font-bold uppercase text-slate-500">{n.type}</td>
                               <td className="py-4 text-right font-mono text-red-500">{(n.anomaly_score || 0).toFixed(4)}</td>
                            </tr>
                          ))}
                       </tbody>
                    </table>
                 </div>
              )}
           </div>

           {/* Integrated Command Footer */}
           <div className="h-10 bg-[#0f172a] border-t border-slate-800 px-6 flex items-center justify-between text-[10px] font-mono text-slate-500">
              <div className="flex gap-6">
                 <span>NODES: {incidentData.nodes_count}</span>
                 <span>EDGES: {incidentData.edges_count}</span>
              </div>
              <div className="flex gap-4 items-center">
                 <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                    <span>SYSTEM_COMM_ACTIVE</span>
                 </div>
                 <span>DB_PORT: 5432</span>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}