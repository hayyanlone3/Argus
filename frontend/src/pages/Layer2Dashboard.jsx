// src/pages/Layer2Dashboard.jsx
import React, { useEffect, useMemo, useState } from 'react';
import apiClient from '../config/api';

function Badge({ decision }) {
  const cls =
    decision === 'MALWARE ALERT'
      ? 'bg-red-600 text-white'
      : decision === 'SUSPICIOUS'
      ? 'bg-yellow-500 text-black'
      : 'bg-green-600 text-white';
  return <span className={`px-2 py-1 rounded text-xs font-semibold ${cls}`}>{decision}</span>;
}

function pct(x) {
  const n = Number(x);
  if (!Number.isFinite(n)) return '0%';
  return `${Math.round(n * 100)}%`;
}

function mono(s) {
  return <span className="font-mono text-xs text-slate-600">{s}</span>;
}

export default function Layer2Dashboard() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const [error, setError] = useState(null);

  const fetchLatest = async (initial = false) => {
    try {
      if (initial) setLoading(true);
      else setRefreshing(true);

      const resp = await apiClient.get('/layer2/live/latest', { 
        params: { limit: 50, suspicious_only: !showAll } 
      });
      const data = resp.data?.items || [];
      setItems(data);
      setError(null);

      // Use the callback form to avoid the stale closure bug
      setSelected((prevSelected) => {
        // If nothing is selected yet, select the first item
        if (!prevSelected && data.length > 0) {
          return data[0];
        }
        // If an item is already selected, keep it selected!
        // We also find the latest version of it in the new data so the right panel stays live.
        if (prevSelected) {
          const freshVersion = data.find(it => it.event?.event_id === prevSelected.event?.event_id);
          return freshVersion || prevSelected;
        }
        return prevSelected;
      });
      
    } catch (e) {
      setError(e?.message || 'Failed to load live scoring data');
    } finally {
      if (initial) setLoading(false);
      else setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchLatest(true);
    const id = setInterval(() => fetchLatest(false), 2000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showAll]);

  const header = useMemo(() => {
    const count = items.length;
    return `${count} live events`;
  }, [items]);

  if (loading) {
    return (
      <div className="p-4">
        <div className="text-slate-800 font-semibold">Layer 2: Scoring Engine</div>
        <div className="text-slate-500 text-sm font-mono">loading…</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-slate-900 text-xl font-semibold tracking-wide">
              Live Scoring
            </div>
          </div>

          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer">
              <input
                type="checkbox"
                checked={showAll}
                onChange={(e) => setShowAll(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              Show all events
            </label>
            <div className="flex items-center gap-2">
              <div className="text-xs font-mono text-slate-500">
                {refreshing ? 'syncing…' : 'live'}
              </div>
              <div className={`h-2 w-2 rounded-full ${refreshing ? 'bg-yellow-400' : 'bg-green-500'}`} />
            </div>
          </div>
        </div>

        {error && (
          <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-red-700 text-sm">
            {error}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Left: event list */}
        <div className="xl:col-span-2 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <div className="text-slate-900 font-semibold">Event Stream</div>
            <div className="text-xs text-slate-500 font-mono">/api/layer2/live/latest</div>
          </div>

          <div className="space-y-2 max-h-[620px] overflow-y-auto pr-1">
            {items.map((it) => {
              const evt = it.event || {};
              const fusion = it.fusion || {};
              const scores = it.scores || {};
              const a = scores?.A?.score ?? 0;
              const b = scores?.B?.score ?? 0;
              const c = scores?.C?.score ?? 0;

              const title =
                evt.kind === 'PROCESS_CREATE'
                  ? `${(evt.parent_process || '').split('\\').pop()} → ${(evt.child_process || '').split('\\').pop()}`
                  : evt.kind === 'FILE_CREATE'
                  ? `FILE: ${(evt.target_path || '').split('\\').pop()}`
                  : evt.kind === 'REG_SET'
                  ? `REG: ${(evt.reg_target || '').slice(0, 60)}`
                  : evt.kind || 'EVENT';

              return (
                <button
                  key={evt.event_id}
                  onClick={() => setSelected(it)}
                  className={[
                    "w-full text-left rounded-lg border p-3 transition",
                    selected?.event?.event_id === evt.event_id
                      ? "border-slate-400 bg-white shadow-sm ring-1 ring-slate-200"
                      : "border-slate-200 bg-slate-50 hover:bg-white",
                  ].join(" ")}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-slate-900 font-semibold">{title || '—'}</div>
                      <div className="text-xs text-slate-500 font-mono mt-1">
                        {evt.kind} {evt.source} {evt.event_id}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <Badge decision={fusion.decision || 'NORMAL'} />
                      <div className="text-xs text-slate-500 font-mono">
                        final={Number(fusion.final_score ?? 0).toFixed(3)}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 mt-3">
                    <div className="rounded-md border border-slate-200 bg-white px-2 py-2">
                      <div className="text-[10px] text-slate-500 font-mono">A</div>
                      <div className="text-sm text-slate-900 font-semibold">{pct(a)}</div>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-white px-2 py-2">
                      <div className="text-[10px] text-slate-500 font-mono">B</div>
                      <div className="text-sm text-slate-900 font-semibold">{pct(b)}</div>
                    </div>
                    <div className="rounded-md border border-slate-200 bg-white px-2 py-2">
                      <div className="text-[10px] text-slate-500 font-mono">C</div>
                      <div className="text-sm text-slate-900 font-semibold">{pct(c)}</div>
                    </div>
                  </div>

                  <div className="text-xs text-slate-500 font-mono mt-2">
                    rule: {fusion.rule || '—'}
                  </div>
                </button>
              );
            })}

            {items.length === 0 && (
              <div className="text-slate-500 text-sm">
                No live events yet. Confirm SysmonCollector is enabled and backend is running.
              </div>
            )}
          </div>
        </div>

        {/* Right: detail */}
        <div className="xl:col-span-1 rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm">
          <div className="text-slate-900 font-semibold mb-2">Selected Event</div>

          {!selected ? (
            <div className="text-slate-500 text-sm">Click an event on the left.</div>
          ) : (
            <div className="space-y-3">
              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs text-slate-500 font-mono">DECISION</div>
                  <Badge decision={selected?.fusion?.decision || 'NORMAL'} />
                </div>
                <div className="text-slate-900 text-lg font-semibold mt-2">
                  final_score={Number(selected?.fusion?.final_score ?? 0).toFixed(3)}
                </div>
                <div className="text-xs text-slate-500 font-mono mt-1">
                  {selected?.fusion?.rule || '—'}
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <div className="text-xs text-slate-500 font-mono mb-2">EVENT</div>
                <div className="space-y-1">
                  <div>{mono(`event_id: ${selected?.event?.event_id}`)}</div>
                  <div>{mono(`kind: ${selected?.event?.kind}`)}</div>
                  <div>{mono(`session_id: ${selected?.event?.session_id}`)}</div>
                  {selected?.event?.parent_process && <div>{mono(`parent: ${selected.event.parent_process}`)}</div>}
                  {selected?.event?.child_process && <div>{mono(`child: ${selected.event.child_process}`)}</div>}
                  {selected?.event?.target_path && <div>{mono(`file: ${selected.event.target_path}`)}</div>}
                  {selected?.event?.reg_target && <div>{mono(`reg: ${selected.event.reg_target}`)}</div>}
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <div className="text-xs text-slate-500 font-mono mb-2">SCORES</div>
                <div className="space-y-2">
                  {['A', 'B', 'C'].map((k) => (
                    <div key={k} className="border border-slate-200 rounded-md bg-slate-50 p-2">
                      <div className="flex items-center justify-between">
                        <div className="text-xs text-slate-600 font-mono">{k}</div>
                        <div className="text-xs text-slate-500 font-mono">
                          {pct(selected?.scores?.[k]?.score ?? 0)}
                        </div>
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        {(selected?.scores?.[k]?.reasons || []).slice(0, 4).join(', ') || '—'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <div className="text-xs text-slate-500 font-mono mb-2">AUTO RESPONSE</div>

                {selected?.fusion?.auto_response ? (
                  <div className="space-y-2 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-600 font-mono">enabled</span>
                      <span className="font-mono text-slate-900">
                        {String(selected.fusion.auto_response.enabled)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-slate-600 font-mono">should_kill</span>
                      <span className="font-mono text-slate-900">
                        {String(selected.fusion.auto_response.should_kill)}
                      </span>
                    </div>

                    <div className="flex items-center justify-between">
                      <span className="text-slate-600 font-mono">killed</span>
                      <span className={`font-mono ${selected.fusion.auto_response.killed ? 'text-red-700' : 'text-slate-900'}`}>
                        {String(selected.fusion.auto_response.killed)}
                      </span>
                    </div>

                    {selected.fusion.auto_response.fast_path !== undefined && (
                      <div className="flex items-center justify-between">
                        <span className="text-slate-600 font-mono">fast_path</span>
                        <span className="font-mono text-slate-900">
                          {String(selected.fusion.auto_response.fast_path)} {selected.fusion.auto_response.fast_reason ? `(${selected.fusion.auto_response.fast_reason})` : ''}
                        </span>
                      </div>
                    )}

                    {selected.fusion.auto_response.child_pid && (
                      <div className="text-slate-700">
                        {mono(`child_pid: ${selected.fusion.auto_response.child_pid}`)}
                      </div>
                    )}
                    {selected.fusion.auto_response.child_process && (
                      <div className="text-slate-700">
                        {mono(`child_process: ${selected.fusion.auto_response.child_process}`)}
                      </div>
                    )}

                    {selected?.fusion?.auto_response?.quarantine && (
                      <div className="mt-2 rounded-md border border-slate-200 bg-slate-50 p-2">
                        <div className="text-[10px] text-slate-500 font-mono mb-1">QUARANTINE</div>
                        <div className="text-slate-700">
                          {mono(`quarantined: ${String(selected.fusion.auto_response.quarantine.quarantined)}`)}
                        </div>
                        {selected.fusion.auto_response.quarantine.original_path && (
                          <div className="text-slate-700">
                            {mono(`original_path: ${selected.fusion.auto_response.quarantine.original_path}`)}
                          </div>
                        )}
                        {selected.fusion.auto_response.quarantine.quarantine_path && (
                          <div className="text-slate-700">
                            {mono(`quarantine_path: ${selected.fusion.auto_response.quarantine.quarantine_path}`)}
                          </div>
                        )}
                        {selected.fusion.auto_response.quarantine.reason && (
                          <div className="text-slate-500">
                            {mono(`reason: ${selected.fusion.auto_response.quarantine.reason}`)}
                          </div>
                        )}
                      </div>
                    )}

                    {selected.fusion.auto_response.error && (
                      <div className="text-red-700">{mono(`error: ${selected.fusion.auto_response.error}`)}</div>
                    )}
                  </div>
                ) : (
                  <div className="text-slate-500 text-sm">—</div>
                )}
              </div>

              <button
                onClick={() => fetchLatest(false)}
                className="w-full px-3 py-2 rounded-lg bg-slate-800 text-white hover:bg-slate-700 transition-colors text-sm font-semibold shadow-sm"
              >
                Refresh now
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}