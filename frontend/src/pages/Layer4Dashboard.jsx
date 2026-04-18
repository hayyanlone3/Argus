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
    // later: fetch from backend config endpoint if you add one
    return String.raw`C:\ProgramData\ARGUS\quarantine`;
  }, []);

  useEffect(() => {
    axios.get('/api/layer4/policy')
      .then(res => setPolicy(res.data))
      .finally(() => setPolicyLoading(false));
  }, []);
  
  const updatePolicy = (fields) => {
    if (!policy) return;
    const next = { ...policy, ...fields };
    setPolicy(next); // instant UI
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
                Automated threat containment: quarantine • whitelist • isolation (policy-driven)
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
          hint="Files moved here are safe from execution. Restore only after verification."
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
                
                {policy?.auto_response_enabled && (
                  <div className="flex flex-col gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-lg ml-2 relative before:absolute before:left-[-9px] before:top-5 before:w-2 before:h-px before:bg-slate-300 before:content-[''] after:absolute after:left-[-9px] after:top-[-12px] after:w-px after:h-7 after:bg-slate-300 after:content-['']">
                    <label className="flex items-center gap-3 cursor-pointer text-sm font-semibold text-slate-700 hover:text-slate-900 transition-colors">
                      <input
                        type="checkbox"
                        checked={!!policy?.kill_on_alert}
                        onChange={e => updatePolicy({ kill_on_alert: e.target.checked })}
                        className="w-4 h-4 text-red-600 bg-white border-gray-300 rounded focus:ring-red-500 focus:ring-2 cursor-pointer"
                      />
                      Kill Process on Malware Alert
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer text-sm font-semibold text-slate-700 hover:text-slate-900 transition-colors">
                      <input
                        type="checkbox"
                        checked={!!policy?.quarantine_on_warn}
                        onChange={e => updatePolicy({ quarantine_on_warn: e.target.checked })}
                        className="w-4 h-4 text-amber-500 bg-white border-gray-300 rounded focus:ring-amber-500 focus:ring-2 cursor-pointer"
                      />
                      Quarantine File on WARN
                    </label>
                  </div>
                )}
              </div>
            )
          }
          hint="When enabled, Argus will actively contain threats based on the specific rules toggled above."
        />

        <InfoCard
          title="RECOMMENDED ACTION STRATEGY"
          value={
            <div className="flex flex-col gap-2 mt-1">
              <div className="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-lg px-4 py-2">
                <span className="text-sm font-bold text-amber-800">SUSPICIOUS</span>
                <ArrowRight className="h-4 w-4 text-amber-400" />
                <span className="text-sm font-bold text-amber-700">ALERT ONLY</span>
              </div>
              <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-lg px-4 py-2">
                <span className="text-sm font-bold text-red-800">MALWARE ALERT</span>
                <ArrowRight className="h-4 w-4 text-red-400" />
                <span className="text-sm font-bold text-red-700">CONTAIN</span>
              </div>
            </div>
          }
          hint="Use least-privilege containment to minimize the operational impact of false positives."
        />
      </div>

      {/* Tabs Navigation */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 border-t border-slate-200">
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
        <TabButton
          active={activeTab === 'about'}
          onClick={() => setActiveTab('about')}
          icon={<Info className="w-5 h-5" />}
          title="Engine Capabilities"
          subtitle="System documentation & safety"
        />
      </div>

      {/* Tab Content Area */}
      <div className="pt-2">
        {activeTab === 'quarantine' && (
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
            <div className="xl:col-span-3 rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden flex flex-col h-full">
              <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="bg-rose-100 p-2 rounded-lg border border-rose-200 text-rose-600">
                    <ShieldAlert className="w-5 h-5" />
                  </div>
                  <h2 className="text-lg font-bold text-slate-900">Quarantined Files</h2>
                </div>
                <div className="bg-white rounded-md px-3 py-1.5 text-xs font-bold text-slate-600 tracking-wider border border-slate-200 shadow-sm uppercase flex items-center gap-2">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  Live View
                </div>
              </div>
              <div className="p-6 bg-white flex-grow">
                <QuarantineList />
              </div>
            </div>

            <div className="xl:col-span-1 space-y-6">
              <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
                <h3 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                  <Database className="h-5 w-5 text-indigo-500" />
                  Storage Location
                </h3>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 mb-4">
                  <span className="font-mono text-xs text-slate-700 break-all">{quarantineDir}</span>
                </div>
                <div className="flex items-start gap-3 p-4 bg-amber-50 rounded-lg border border-amber-200">
                  <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0" />
                  <p className="text-xs font-medium text-amber-800 leading-relaxed">
                    Keep this folder ACL-restricted. Restores should only be performed via explicit analyst action in this dashboard.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'whitelist' && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <div className="xl:col-span-2 rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden flex flex-col h-full">
              <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center justify-between">
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
                  <div className="relative pl-6 before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-slate-300 before:rounded-full before:content-['']">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 rounded text-[10px] font-extrabold tracking-wider bg-slate-100 text-slate-600 border border-slate-200">TIER 1</span>
                      <h4 className="text-sm font-bold text-slate-800">Path Only</h4>
                    </div>
                    <p className="text-slate-500 text-xs font-medium leading-relaxed">
                      Lowest friction; trusts location entirely. Recommended only for strictly controlled vendor install paths.
                    </p>
                  </div>

                  <div className="relative pl-6 before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-blue-400 before:rounded-full before:content-['']">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 rounded text-[10px] font-extrabold tracking-wider bg-blue-50 text-blue-600 border border-blue-200">TIER 2</span>
                      <h4 className="text-sm font-bold text-slate-800">Path + Hash</h4>
                    </div>
                    <p className="text-slate-500 text-xs font-medium leading-relaxed">
                      Version-controlled trust. Provides the best optimal balance of operational safety and administrative usability.
                    </p>
                  </div>

                  <div className="relative pl-6 before:absolute before:left-0 before:top-2 before:w-2 before:h-2 before:bg-indigo-500 before:rounded-full before:content-['']">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-2 py-0.5 rounded text-[10px] font-extrabold tracking-wider bg-indigo-50 text-indigo-600 border border-indigo-200">TIER 3</span>
                      <h4 className="text-sm font-bold text-slate-800">Hash Only</h4>
                    </div>
                    <p className="text-slate-500 text-xs font-medium leading-relaxed">
                      Trusts a specific, verified file version regardless of execution location. Use sparingly.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'about' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-6">
                <div className="bg-indigo-100 p-2 rounded-lg border border-indigo-200 text-indigo-600">
                  <Cpu className="h-6 w-6" />
                </div>
                <h3 className="text-xl font-extrabold text-slate-900">Engine Capabilities</h3>
              </div>
              
              <ul className="space-y-4">
                <li className="flex items-start gap-3 p-3 rounded-lg hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100">
                  <div className="bg-emerald-100 text-emerald-600 p-1 rounded mt-0.5">
                    <Check className="h-3 w-3" />
                  </div>
                  <div>
                    <span className="block text-sm font-bold text-slate-800">Secure Quarantine Workflow</span>
                    <span className="block text-xs font-medium text-slate-500 mt-1">Automated isolation with full forensic preservation and 1-click restoration.</span>
                  </div>
                </li>
                <li className="flex items-start gap-3 p-3 rounded-lg hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100">
                  <div className="bg-emerald-100 text-emerald-600 p-1 rounded mt-0.5">
                    <Check className="h-3 w-3" />
                  </div>
                  <div>
                    <span className="block text-sm font-bold text-slate-800">Tiered Trust Framework</span>
                    <span className="block text-xs font-medium text-slate-500 mt-1">Granular exception handling to eliminate false positives without opening blind spots.</span>
                  </div>
                </li>
                <li className="flex items-start gap-3 p-3 rounded-lg hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100">
                  <div className="bg-emerald-100 text-emerald-600 p-1 rounded mt-0.5">
                    <Check className="h-3 w-3" />
                  </div>
                  <div>
                    <span className="block text-sm font-bold text-slate-800">Process Termination Hooks</span>
                    <span className="block text-xs font-medium text-slate-500 mt-1">Immediate, forceful halting of malicious processes via PID/name interception.</span>
                  </div>
                </li>
                <li className="flex items-start gap-3 p-3 rounded-lg hover:bg-slate-50 transition-colors border border-transparent hover:border-slate-100">
                  <div className="bg-emerald-100 text-emerald-600 p-1 rounded mt-0.5">
                    <Check className="h-3 w-3" />
                  </div>
                  <div>
                    <span className="block text-sm font-bold text-slate-800">Policy-Driven Automation</span>
                    <span className="block text-xs font-medium text-slate-500 mt-1">Gated automated responses driven by layer 2 & 3 ML correlation confidence scores.</span>
                  </div>
                </li>
              </ul>
            </div>

            <div className="flex flex-col gap-6">
              <div className="relative overflow-hidden rounded-xl border border-amber-300 bg-amber-50 p-6 shadow-sm h-full">
                <div className="absolute -top-4 -right-4 p-4 opacity-10">
                  <AlertTriangle className="w-48 h-48" />
                </div>
                <div className="relative z-10">
                  <div className="flex items-center gap-3 mb-5">
                    <div className="bg-amber-100 p-2.5 rounded-lg text-amber-600 shadow-sm">
                      <AlertTriangle className="h-6 w-6" />
                    </div>
                    <h3 className="text-xl font-extrabold text-amber-900">Critical Safety Warning</h3>
                  </div>
                  <p className="text-amber-800 font-medium leading-relaxed text-sm">
                    Auto-response capabilities (<strong className="font-extrabold text-amber-900">Kill</strong> and <strong className="font-extrabold text-amber-900">Quarantine</strong>) should ONLY be enabled globally after extensive tuning of the learning engine thresholds and comprehensive population of the whitelist manager. 
                  </p>
                  <p className="text-amber-800 font-medium leading-relaxed text-sm mt-4 p-4 bg-white/60 rounded-lg border border-amber-200/50">
                    Premature activation without baseline profiling runs a high risk of terminating core OS processes or disrupting legitimate administrative tools via false positives.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}