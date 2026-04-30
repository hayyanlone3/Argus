// src/pages/Layer4Dashboard.jsx
import React, { useMemo, useState, useEffect } from 'react';
import axios from 'axios';
import QuarantineList from '../components/quarantine/QuarantineList';
import WhitelistManager from '../components/whitelist/WhitelistManager';
import { 
  ShieldCheck, 
  FolderLock, 
  Loader2, 
  ArrowRight, 
  ShieldAlert, 
  CheckCircle, 
  Info, 
  Database, 
  AlertTriangle, 
  Cpu, 
  Check 
} from 'lucide-react';

function TabButton({ active, onClick, icon, title, subtitle }) {
  return (
    <button
      onClick={onClick}
      className={[
        "flex-1 text-left rounded-xl border px-5 py-4 transition-all duration-200 shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500",
        active
          ? "border-blue-400 bg-blue-50 ring-1 ring-blue-400 shadow-md"
          : "border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300",
      ].join(" ")}
    >
      <div className="flex items-start gap-4">
        <div className={`p-2.5 rounded-lg flex items-center justify-center transition-colors ${active ? 'bg-blue-600 text-white shadow-sm' : 'bg-slate-100 text-slate-500'}`}>
          {icon}
        </div>
        <div>
          <div className={`font-bold tracking-tight ${active ? 'text-blue-900' : 'text-slate-700'}`}>{title}</div>
          <div className={`text-xs font-medium mt-1 leading-relaxed ${active ? 'text-blue-700' : 'text-slate-500'}`}>{subtitle}</div>
        </div>
      </div>
    </button>
  );
}

function InfoCard({ title, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow duration-200 flex flex-col h-full">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-1.5 h-1.5 rounded-full bg-indigo-500"></div>
        <div className="text-xs font-bold text-slate-500 tracking-wider uppercase">{title}</div>
      </div>
      <div className="text-slate-900 font-medium mt-1 flex-grow">{value}</div>
      {hint && (
        <div className="mt-4 pt-3 border-t border-slate-100">
          <div className="text-xs font-medium text-slate-500 leading-relaxed">{hint}</div>
        </div>
      )}
    </div>
  );
}

export default function Layer4Dashboard() {
  const [activeTab, setActiveTab] = useState('quarantine');
  const [policy, setPolicy] = useState(null);
  const [policyLoading, setPolicyLoading] = useState(true);

  const quarantineDir = useMemo(() => {
    return String.raw`C:\ProgramData\ARGUS\quarantine`;
  }, []);

  useEffect(() => {
    axios.get('/api/layer4/policy')
      .then(res => {
        if (res.data && typeof res.data === 'object') {
          setPolicy(res.data);
        }
      })
      .catch(err => {
        console.error("  Policy Fetch Failed. Using local defaults.", err);
      })
      .finally(() => setPolicyLoading(false));
  }, []);
  
  const updatePolicy = (fields) => {
    if (!policy) return;
    const next = { ...policy, ...fields };
    setPolicy(next);
    axios.post('/api/layer4/policy', next)
      .then(res => setPolicy(res.data));
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-10">
      {/* Header */}
      <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md border border-indigo-300">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
                Layer 4 <span className="text-slate-300 mx-2 font-normal">|</span> Response Engine
              </h1>
              <p className="text-slate-500 text-sm font-medium mt-1">
                Automated threat containment: quarantine whitelist isolation
              </p>
            </div>
          </div>

          <div className={`flex flex-col items-end rounded-xl border px-5 py-3 shadow-inner ${policy?.auto_response_enabled ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'}`}>
            <div className={`text-[10px] font-extrabold tracking-widest uppercase ${policy?.auto_response_enabled ? 'text-red-500' : 'text-emerald-600'}`}>System Mode</div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${policy?.auto_response_enabled ? 'bg-red-400' : 'bg-emerald-400'}`}></span>
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${policy?.auto_response_enabled ? 'bg-red-500' : 'bg-emerald-500'}`}></span>
              </span>
              <div className={`text-base font-extrabold tracking-tight ${policy?.auto_response_enabled ? 'text-red-700' : 'text-emerald-800'}`}>
                {policy?.auto_response_enabled ? 'Active Response' : 'Passive Monitoring'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <InfoCard
          title="QUARANTINE DIRECTORY"
          value={
            <div className="bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 flex items-center overflow-hidden">
              <FolderLock className="h-4 w-4 text-slate-400 mr-2 flex-shrink-0" />
              <span className="font-mono text-sm text-slate-700 truncate" title={quarantineDir}>{quarantineDir}</span>
            </div>
          }
        />
        
        <InfoCard
          title="AUTO-RESPONSE POLICY"
          value={
            policyLoading ? (
              <div className="flex items-center gap-2 text-slate-400 font-medium">
                <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
                Loading...
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                <label className="flex items-center gap-3 cursor-pointer group">
                  <div className="relative">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={!!policy?.auto_response_enabled}
                      onChange={e => updatePolicy({ auto_response_enabled: e.target.checked })}
                    />
                    <div className="w-11 h-6 bg-slate-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-red-200 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-500 shadow-inner"></div>
                  </div>
                  <span className={`text-sm font-bold ${policy?.auto_response_enabled ? "text-red-600" : "text-slate-600 group-hover:text-slate-800"}`}>
                    {policy?.auto_response_enabled ? "Master Switch: ENABLED" : "Master Switch: DISABLED"}
                  </span>
                </label>
              </div>
            )
          }
          hint="When enabled, Argus will actively contain threats."
        />

        <InfoCard
          title="STRATEGY"
          value={
            <div className="flex flex-col gap-2 mt-1">
              <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-lg px-4 py-2">
                <span className="text-sm font-bold text-red-800">MALWARE</span>
                <ArrowRight className="h-4 w-4 text-red-400" />
                <span className="text-sm font-bold text-red-700">CONTAIN</span>
              </div>
            </div>
          }
          hint="Least-privilege containment active."
        />
      </div>

      {/* Tabs Navigation */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-slate-200">
        <TabButton
          active={activeTab === 'quarantine'}
          onClick={() => setActiveTab('quarantine')}
          icon={<ShieldAlert className="w-5 h-5" />}
          title="Quarantine Manager"
          subtitle="Isolate & review suspicious files"
        />
        <TabButton
          active={activeTab === 'whitelist'}
          onClick={() => setActiveTab('whitelist')}
          icon={<CheckCircle className="w-5 h-5" />}
          title="Whitelist Rules"
          subtitle="Configure trusted entities (tiers 1-3)"
        />
      </div>

      {/* Tab Content Area */}
      {activeTab === 'quarantine' && (
        <div className="flex justify-center w-full">
          
            
            <div className="px-2 pb-6 overflow-x-auto">
              <div className="rounded-lg border-2 border-slate-300 bg-white shadow-inner">
                {/* Enhanced table visuals for QuarantineList */}
                <div className="overflow-x-auto">
                  <div className="min-w-full">
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="bg-slate-100 border-b-2 border-slate-300">
                        </tr>
                      </thead>
                      <tbody>
                        <QuarantineList
                          renderRow={filePath => (
                            <tr key={filePath} className="even:bg-slate-50 odd:bg-white border-b border-slate-200 hover:bg-blue-50 transition">
                              <td className="px-4 py-2 font-mono text-xs text-slate-800 whitespace-nowrap max-w-[500px] overflow-hidden text-ellipsis" title={filePath}>
                                {filePath}
                              </td>
                            </tr>
                          )}
                        />
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>
      )}

      {activeTab === 'whitelist' && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden flex flex-col h-full">
            <div className="bg-slate-50 border-b border-slate-200 px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="bg-emerald-100 p-2 rounded-lg border border-emerald-200 text-emerald-600">
                  <CheckCircle className="h-5 w-5" />
                </div>
                <h2 className="text-lg font-bold text-slate-900">Whitelist Rules</h2>
              </div>
            </div>
            <div className="p-6 bg-white flex-grow">
              <WhitelistManager />
            </div>
          </div>

          <div className="xl:col-span-1">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm h-full">
              <h3 className="text-base font-extrabold text-slate-900 mb-5 pb-3 border-b border-slate-100">Trust Architecture</h3>
              <div className="space-y-5">
                <div className="relative pl-6 before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-slate-300 before:rounded-full">
                  <h4 className="text-sm font-bold text-slate-800">Path Only</h4>
                  <p className="text-slate-500 text-xs font-medium mt-1">Trusts file location.</p>
                </div>
                <div className="relative pl-6 before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-blue-400 before:rounded-full">
                  <h4 className="text-sm font-bold text-slate-800">Path + Hash</h4>
                  <p className="text-slate-500 text-xs font-medium mt-1">Version-controlled trust.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}