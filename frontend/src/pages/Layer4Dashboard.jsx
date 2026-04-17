// src/pages/Layer4Dashboard.jsx
import React, { useMemo, useState } from 'react';
import QuarantineList from '../components/quarantine/QuarantineList';
import WhitelistManager from '../components/whitelist/WhitelistManager';

function TabButton({ active, onClick, icon, title, subtitle }) {
  return (
    <button
      onClick={onClick}
      className={[
        "flex-1 text-left rounded-xl border px-4 py-3 transition shadow-sm",
        active
          ? "border-slate-300 bg-white ring-1 ring-slate-200"
          : "border-slate-200 bg-slate-50 hover:bg-white",
      ].join(" ")}
    >
      <div className="flex items-start gap-3">
        <div className="text-xl">{icon}</div>
        <div>
          <div className="text-slate-900 font-semibold">{title}</div>
          <div className="text-xs text-slate-500 font-mono mt-0.5">{subtitle}</div>
        </div>
      </div>
    </button>
  );
}

function InfoCard({ title, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
      <div className="text-xs text-slate-500 font-mono">{title}</div>
      <div className="text-slate-900 font-semibold mt-1">{value}</div>
      {hint && <div className="text-xs text-slate-500 mt-2">{hint}</div>}
    </div>
  );
}

export default function Layer4Dashboard() {
  const [activeTab, setActiveTab] = useState('quarantine');

  const quarantineDir = useMemo(() => {
    // later: fetch from backend config endpoint if you add one
    return String.raw`C:\ProgramData\ARGUS\quarantine`;
  }, []);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="text-slate-900 text-xl font-semibold tracking-wide">
              Layer 4 • Response Engine
            </div>
            <div className="text-slate-500 text-sm font-mono">
              Automated threat containment: quarantine • whitelist • isolation (policy-driven)
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <div className="text-[10px] text-slate-500 font-mono">MODE</div>
            <div className="text-slate-900 text-sm font-semibold">Monitoring</div>
          </div>
        </div>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <InfoCard
          title="QUARANTINE DIRECTORY"
          value={<span className="font-mono text-sm text-slate-700">{quarantineDir}</span>}
          hint="Files moved here are safe from execution. Restore only after verification."
        />
        <InfoCard
          title="AUTO-RESPONSE"
          value="Disabled (recommended during tuning)"
          hint="When enabled, Argus can kill/quarantine on MALWARE ALERT."
        />
        <InfoCard
          title="RECOMMENDED POLICY"
          value="SUSPICIOUS → alert | MALWARE ALERT → contain"
          hint="Use least-privilege containment to reduce false positives impact."
        />
      </div>

      {/* Tabs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <TabButton
          active={activeTab === 'quarantine'}
          onClick={() => setActiveTab('quarantine')}
          icon="🚫"
          title="Quarantine"
          subtitle="Move suspicious files to isolated directory"
        />
        <TabButton
          active={activeTab === 'whitelist'}
          onClick={() => setActiveTab('whitelist')}
          icon="✅"
          title="Whitelist"
          subtitle="Tiered trust rules (path/hash)"
        />
        <TabButton
          active={activeTab === 'about'}
          onClick={() => setActiveTab('about')}
          icon="ℹ️"
          title="About"
          subtitle="Capabilities and safety guidance"
        />
      </div>

      {/* Content */}
      {activeTab === 'quarantine' && (
        <div className="space-y-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="text-slate-900 font-semibold">Quarantined Files</div>
              <div className="text-xs text-slate-500 font-mono">live list</div>
            </div>
            <QuarantineList />
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
            <div className="text-slate-900 font-semibold">Quarantine Directory</div>
            <div className="mt-2 rounded-lg border border-slate-200 bg-white p-3">
              <span className="font-mono text-sm text-slate-700">{quarantineDir}</span>
            </div>
            <div className="text-xs text-slate-500 mt-2">
              Tip: keep this folder ACL-restricted. Restores should be explicit analyst actions.
            </div>
          </div>
        </div>
      )}

      {activeTab === 'whitelist' && (
        <div className="space-y-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="text-slate-900 font-semibold">Whitelist Manager</div>
              <div className="text-xs text-slate-500 font-mono">tiers 1–3</div>
            </div>
            <WhitelistManager />
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
            <div className="text-slate-900 font-semibold mb-2">Tier System</div>

            <div className="space-y-2 text-sm">
              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <div className="text-slate-900 font-semibold">Tier 1: Path Only</div>
                <div className="text-slate-500 text-xs mt-1">
                  Lowest friction; trusts location. Good for vendor install paths.
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <div className="text-slate-900 font-semibold">Tier 2: Path + Hash</div>
                <div className="text-slate-500 text-xs mt-1">
                  Version-controlled trust. Best balance of safety and usability.
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <div className="text-slate-900 font-semibold">Tier 3: Hash Only</div>
                <div className="text-slate-500 text-xs mt-1">
                  Trusts a specific file version anywhere (use sparingly).
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'about' && (
        <div className="space-y-3">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
            <div className="text-slate-900 font-semibold mb-2">Layer 4 Capabilities</div>
            <ul className="space-y-2 text-sm text-slate-700">
              <li><span className="font-mono text-xs text-slate-500">✓</span> File quarantine / restore workflow</li>
              <li><span className="font-mono text-xs text-slate-500">✓</span> Whitelist tiers to reduce false positives</li>
              <li><span className="font-mono text-xs text-slate-500">✓</span> Process isolation hooks (kill by PID/name)</li>
              <li><span className="font-mono text-xs text-slate-500">✓</span> Policy-driven auto-response (recommended gated)</li>
            </ul>
          </div>

          <div className="rounded-xl border border-yellow-200 bg-yellow-50 p-4 shadow-sm">
            <div className="text-yellow-800 font-semibold">Safety note</div>
            <div className="text-yellow-700 text-sm mt-1">
              Auto-response should be enabled only after tuning thresholds and whitelists to avoid impacting legitimate tools.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}