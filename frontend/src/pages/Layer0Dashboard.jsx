// src/pages/Layer0Dashboard.jsx
import React, { useState, useEffect } from 'react';
import LoadingSpinner from '../components/common/LoadingSpinner';
import apiClient from '../config/api';

export default function Layer0Dashboard() {
  const [recentScans, setRecentScans] = useState([]);
  const [loadingScans, setLoadingScans] = useState(true);

  // Fetch recent background scans from kernel telemetry
  const fetchRecentScans = async () => {
    try {
      const response = await apiClient.get('/layer0/recent-analysis?limit=25');
      setRecentScans(response.data);
    } catch (err) {
      console.error('Failed to fetch scans:', err);
    } finally {
      setLoadingScans(false);
    }
  };

  useEffect(() => {
    fetchRecentScans();
    const interval = setInterval(fetchRecentScans, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            Layer 0: Autonomous Bouncer
          </h1>
          <p className="text-slate-500 mt-2 ml-14 max-w-2xl">
            Real-time kernel telemetry analysis via Sysmon. Files are automatically analyzed and quarantined 
            at the point of creation without manual intervention.
          </p>
        </div>
        <div className="flex gap-2">
            <div className="flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-700 text-[10px] font-black rounded-xl border border-emerald-100 uppercase tracking-widest animate-pulse">
                <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
                Kernel Monitoring Active
            </div>
            <div className="px-4 py-2 bg-indigo-50 text-indigo-700 text-[10px] font-black rounded-xl border border-indigo-100 uppercase tracking-widest">
                Auto-Response Enabled
            </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Detection Insights Panel */}
        <div className="xl:col-span-1 space-y-6">
          <div className="bg-slate-900 rounded-2xl p-6 text-white shadow-2xl overflow-hidden relative border border-slate-800">
            <div className="absolute top-0 right-0 p-8 opacity-5 pointer-events-none transform translate-x-4 -translate-y-4">
            </div>
            <h3 className="font-bold text-lg mb-6 flex items-center gap-3 border-b border-slate-700 pb-4">
              <span className="text-indigo-400"></span> Security Policy
            </h3>
            <div className="space-y-6">
                <div>
                    <h4 className="text-[10px] uppercase tracking-widest font-black text-indigo-400 mb-2">Entropy Threshold</h4>
                    <div className="flex items-end gap-2">
                        <span className="text-3xl font-black">7.90</span>
                        <span className="text-xs text-slate-500 mb-1">bits</span>
                    </div>
                </div>
                <div className="space-y-4">
                    <p className="text-xs text-slate-400 leading-relaxed italic">
                        "Files exceeding 7.90 entropy or failing VT lookup are instantly moved to the 
                        quarantine vault to prevent execution."
                    </p>
                    <div className="pt-4 border-t border-slate-800">
                        <ul className="space-y-4">
                            {[
                                {label: "VirusTotal Lookup"},
                                {label: "Entropy Verification"},
                                {label: "Signature Validation"},
                                {label: "Auto-Quarantine"}
                            ].map((item, i) => (
                                <li key={i} className="flex items-center gap-3 text-xs font-semibold text-slate-200">
                                    {item.label}
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            </div>
          </div>
          
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
             <h4 className="text-xs uppercase tracking-widest font-black text-slate-400 mb-4">Watching Extensions</h4>
             <div className="flex flex-wrap gap-2">
                {[".exe", ".dll", ".ps1", ".vbs", ".js", ".lnk", ".bat", ".com", ".pdf"].map(ext => (
                   <span key={ext} className="px-2 py-1 bg-slate-100 text-slate-600 rounded text-[10px] font-mono font-bold border border-slate-200">{ext}</span>
                ))}
             </div>
          </div>
        </div>

        {/* Live Autonomous Stream */}
        <div className="xl:col-span-3">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden h-full flex flex-col">
            <div className="px-8 py-6 bg-white border-b border-slate-100 flex justify-between items-center">
                <div>
                    <h3 className="font-black text-slate-800 text-xl flex items-center gap-3 tracking-tight">
                        Live Autonomous Stream
                    </h3>
                    <p className="text-xs text-slate-400 font-medium">Monitoring kernel events at the storage layer</p>
                </div>
                <div className="flex items-center gap-4">
                    <div className="text-right">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Active Sources</p>
                        <p className="text-xs font-bold text-slate-600">Microsoft-Windows-Sysmon</p>
                    </div>
                    <div className="h-8 w-[1px] bg-slate-100 mx-2"></div>
                    <button onClick={fetchRecentScans} className="p-2 hover:bg-slate-50 rounded-full transition-colors text-slate-400">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                    </button>
                </div>
            </div>
            
            <div className="flex-1 overflow-y-auto">
              {loadingScans ? (
                <div className="h-full flex items-center justify-center py-20"><LoadingSpinner size="lg" /></div>
              ) : recentScans.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center py-20 text-center px-10">
                    <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center text-4xl mb-4 text-slate-200"> </div>
                    <h4 className="font-bold text-slate-400">Awaiting Kernel Events</h4>
                    <p className="text-xs text-slate-300 max-w-xs mt-2 italic">The system is operational and listening. Create or download a file to see real-time analysis.</p>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead className="sticky top-0 z-10">
                    <tr className="bg-slate-50/80 backdrop-blur-sm text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-slate-200">
                      <th className="px-8 py-4">Event Time</th>
                      <th className="px-8 py-4">Detection Target</th>
                      <th className="px-8 py-4">Entropy Profile</th>
                      <th className="px-8 py-4">Verdict</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {recentScans.map((scan) => (
                      <tr key={scan.id} className="hover:bg-indigo-50/30 transition-all duration-200 group">
                        <td className="px-8 py-5 text-[11px] text-slate-400 font-mono font-medium">
                          {new Date(scan.timestamp).toLocaleTimeString([], {hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit'})}
                        </td>
                        <td className="px-8 py-5">
                          <div className="flex items-center gap-3">
                             <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm ${
                                scan.status === 'PASS' ? 'bg-emerald-50 text-emerald-500' : scan.status === 'WARN' ? 'bg-amber-50 text-amber-500' : 'bg-rose-50 text-rose-500'
                             }`}>
                                {scan.path.toLowerCase().endsWith('.exe') ? '⚙️' : scan.path.toLowerCase().endsWith('.pdf') ? '📄' : '📝'}
                             </div>
                             <div className="overflow-hidden">
                                <p className="text-xs font-black text-slate-700 truncate max-w-[280px]" title={scan.path}>
                                    {scan.path.split('\\').pop()}
                                </p>
                                <p className="text-[10px] text-slate-400 font-mono italic truncate max-w-[280px]">{scan.path}</p>
                             </div>
                          </div>
                        </td>
                        <td className="px-8 py-5">
                          <div className="flex flex-col gap-1.5 min-w-[120px]">
                            <div className="flex justify-between items-center">
                                <span className={`text-[11px] font-black ${scan.entropy > 7.5 ? (scan.entropy > 7.9 ? 'text-rose-600' : 'text-amber-600') : 'text-slate-600'}`}>
                                    {scan.entropy.toFixed(2)}
                                </span>
                                <span className="text-[9px] font-bold text-slate-300">max 8.0</span>
                            </div>
                            <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                <div className={`h-full rounded-full transition-all duration-1000 ${
                                    scan.entropy > 7.9 ? 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]' : scan.entropy > 7.5 ? 'bg-amber-400' : 'bg-indigo-400'
                                }`} style={{width: `${(scan.entropy/8)*100}%`}}></div>
                            </div>
                          </div>
                        </td>
                        <td className="px-8 py-5">
                          <div className="flex items-center gap-3">
                              <span className={`px-3 py-1.5 rounded-lg text-[10px] font-black border-2 tracking-widest ${
                                scan.status === 'PASS' 
                                  ? 'bg-emerald-50 text-emerald-600 border-emerald-100' 
                                  : scan.status === 'WARN' 
                                  ? 'bg-amber-50 text-amber-600 border-amber-100'
                                  : 'bg-rose-50 text-rose-600 border-rose-100 shadow-sm shadow-rose-100'
                              }`}>
                                {scan.status}
                              </span>
                              {scan.status !== 'PASS' && (
                                 <span className="animate-bounce text-xs" title="Auto-Quarantined"></span>
                              )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}