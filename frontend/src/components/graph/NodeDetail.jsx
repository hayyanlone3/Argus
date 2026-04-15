import React, { useEffect, useState } from "react";
import { graphService } from "../../services/graphService";
import LoadingSpinner from "../common/LoadingSpinner";

function Row({ k, v }) {
  return (
    <div className="flex items-start justify-between gap-4 py-1">
      <div className="text-[11px] text-slate-400 font-mono">{k}</div>
      <div className="text-[12px] text-slate-200 text-right break-all">{v ?? "-"}</div>
    </div>
  );
}

export default function NodeDetail({ nodeId }) {
  const [node, setNode] = useState(null);
  const [neighbors, setNeighbors] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        const [n, neigh] = await Promise.all([
          graphService.getNode(nodeId),
          graphService.getNeighbors(nodeId, 2),
        ]);
        setNode(n);
        setNeighbors(neigh);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    if (nodeId) run();
  }, [nodeId]);

  if (!nodeId) return null;
  if (loading) return <LoadingSpinner />;
  if (error) return <div className="text-red-200">Error: {error}</div>;

  return (
    <div className="rounded-lg border border-slate-700/60 bg-slate-900 p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="text-slate-100 font-semibold">{node?.name || `Node ${nodeId}`}</div>
        <div className="text-xs text-slate-400 font-mono">{(node?.type || "").toUpperCase()}</div>
      </div>

      <div className="border-t border-slate-700/60 pt-2 space-y-1">
        <Row k="id" v={node?.id} />
        <Row k="type" v={node?.type} />
        <Row k="path" v={node?.path} />
        <Row k="hash_sha256" v={node?.hash_sha256} />
        <Row k="path_risk" v={node?.path_risk} />
        <Row k="neighbors" v={neighbors?.neighbor_count} />
      </div>

      {neighbors?.neighbors?.length > 0 && (
        <div className="mt-3 border-t border-slate-700/60 pt-3">
          <div className="text-[11px] text-slate-400 font-mono mb-2">CONNECTED NODES</div>
          <div className="max-h-44 overflow-y-auto space-y-1">
            {neighbors.neighbors.slice(0, 50).map((nid) => (
              <div key={nid} className="text-xs font-mono text-slate-200 bg-slate-950/60 border border-slate-700/60 rounded px-2 py-1">
                Node {nid}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}