import React, { useEffect, useMemo, useRef } from "react";
import * as d3 from "d3";

const BOX = { w: 170, h: 46, r: 10 };

function severityColor(node) {
  // Use whatever is available; default clean
  const lvl = node?.severity || "clean";
  if (lvl === "isolated" || lvl === "critical") return "#ef4444";
  if (lvl === "anomaly" || lvl === "warning") return "#f59e0b";
  return "#334155";
}

function edgeColor(edgeType) {
  if (edgeType === "SPAWNED") return "#60a5fa";
  if (edgeType === "WROTE") return "#f59e0b";
  if (edgeType === "MODIFIED_REG") return "#a78bfa";
  return "#64748b";
}

// Build a tree from edges (best-effort): prefer SPAWNED chain as trunk
function buildTree(seedId, nodes, edges) {
  const nodeById = new Map((nodes || []).map(n => [n.id, { ...n, children: [] }]));
  const get = (id) => nodeById.get(id) || { id, name: `Node ${id}`, type: "unknown", children: [] };

  // adjacency by source
  const out = new Map();
  (edges || []).forEach(e => {
    if (!out.has(e.source_id)) out.set(e.source_id, []);
    out.get(e.source_id).push(e);
  });

  const visited = new Set();
  const root = get(seedId);

  function expand(curr, depth = 0) {
    if (visited.has(curr.id) || depth > 4) return;
    visited.add(curr.id);

    const outs = out.get(curr.id) || [];
    // trunk first: SPAWNED then others
    outs.sort((a,b) => (a.edge_type === "SPAWNED" ? -1 : 1) - (b.edge_type === "SPAWNED" ? -1 : 1));

    for (const e of outs) {
      const child = get(e.target_id);
      // store edge type on child link
      child._via = e.edge_type;
      curr.children.push(child);
      expand(child, depth + 1);
    }
  }

  expand(root, 0);
  return root;
}

export default function D3ProvTree({ seedNodeId, nodes, edges, height = 560, onNodeClick }) {
  const containerRef = useRef(null);
  const svgRef = useRef(null);

  const treeData = useMemo(() => {
    if (!seedNodeId) return null;
    return buildTree(seedNodeId, nodes, edges);
  }, [seedNodeId, nodes, edges]);

  useEffect(() => {
    if (!containerRef.current || !svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = containerRef.current.clientWidth || 900;
    svg.attr("width", width).attr("height", height);

    if (!treeData) return;

    const root = d3.hierarchy(treeData);
    const layout = d3.tree().nodeSize([80, 240]); // vertical gap, horizontal gap
    layout(root);

    // center nicely
    const g = svg.append("g").attr("transform", `translate(${120},${height / 2})`);

    // links
    const linkGen = d3.linkHorizontal().x(d => d.y).y(d => d.x);

    const links = g.append("g")
      .selectAll("path")
      .data(root.links())
      .join("path")
      .attr("d", linkGen)
      .attr("fill", "none")
      .attr("stroke", d => edgeColor(d.target.data._via))
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0.75);

    // link labels (edge type)
    g.append("g")
      .selectAll("text")
      .data(root.links())
      .join("text")
      .attr("x", d => (d.source.y + d.target.y) / 2)
      .attr("y", d => (d.source.x + d.target.x) / 2 - 6)
      .attr("fill", "#94a3b8")
      .attr("font-size", 10)
      .attr("font-family", "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace")
      .text(d => d.target.data._via || "");

    // nodes as groups
    const node = g.append("g")
      .selectAll("g")
      .data(root.descendants())
      .join("g")
      .attr("transform", d => `translate(${d.y},${d.x})`)
      .style("cursor", "pointer")
      .on("click", (event, d) => {
        event.stopPropagation();
        onNodeClick?.(d.data);
      });

    node.append("rect")
      .attr("x", -BOX.w / 2)
      .attr("y", -BOX.h / 2)
      .attr("width", BOX.w)
      .attr("height", BOX.h)
      .attr("rx", BOX.r)
      .attr("fill", "#0b1220")
      .attr("stroke", d => severityColor(d.data))
      .attr("stroke-width", 1.6);

    node.append("text")
      .attr("x", -BOX.w / 2 + 10)
      .attr("y", -6)
      .attr("fill", "#e2e8f0")
      .attr("font-size", 12)
      .attr("font-weight", 650)
      .text(d => (d.data.name || `Node ${d.data.id}`).slice(0, 24));

    node.append("text")
      .attr("x", -BOX.w / 2 + 10)
      .attr("y", 14)
      .attr("fill", "#94a3b8")
      .attr("font-size", 10)
      .attr("font-family", "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace")
      .text(d => `${(d.data.type || "node").toUpperCase()}  ID ${d.data.id}`);

  }, [treeData, height, onNodeClick]);

  return (
    <div ref={containerRef} style={{ width: "100%" }}>
      <svg ref={svgRef} style={{ width: "100%", display: "block" }} />
    </div>
  );
}