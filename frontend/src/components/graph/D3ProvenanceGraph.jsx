import React, { useEffect, useMemo, useRef } from "react";
import * as d3 from "d3";

const NODE_COLORS = {
  process: "#22c55e",
  file: "#3b82f6",
  reg_key: "#f59e0b",
  script: "#a855f7",
  wmi_object: "#ef4444",
  unknown: "#94a3b8",
};

const EDGE_COLORS = {
  SPAWNED: "#22c55e",
  WROTE: "#3b82f6",
  READ: "#64748b",
  MODIFIED_REG: "#f59e0b",
  EXECUTED_SCRIPT: "#a855f7",
  INJECTED_INTO: "#ef4444",
  SUBSCRIBED_WMI: "#ef4444",
  DISABLED_AMSI: "#ef4444",
};

function nodeColor(n) {
  return NODE_COLORS[n?.type] || NODE_COLORS.unknown;
}
function edgeColor(e) {
  return EDGE_COLORS[e?.edge_type] || "#94a3b8";
}

export default function D3ProvenanceGraph({
  nodes,
  edges,
  height = 520,
  onNodeClick,
  selectedNodeId,
}) {
  const containerRef = useRef(null);
  const svgRef = useRef(null);

  const graph = useMemo(() => {
    const ns = (nodes || []).map((n) => ({ ...n, id: n.id }));
    const nodeIds = new Set(ns.map((n) => n.id));

    const ls = (edges || [])
      .filter((e) => nodeIds.has(e.source_id) && nodeIds.has(e.target_id))
      .map((e) => ({ ...e, source: e.source_id, target: e.target_id }));

    return { ns, ls };
  }, [nodes, edges]);

  useEffect(() => {
    if (!containerRef.current || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = containerRef.current.clientWidth || 900;
    svg.attr("width", width).attr("height", height);

    const g = svg.append("g");

    // zoom / pan
    svg.call(
      d3
        .zoom()
        .scaleExtent([0.2, 3])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
        })
    );

    const link = g
      .append("g")
      .attr("stroke-opacity", 0.7)
      .selectAll("line")
      .data(graph.ls)
      .join("line")
      .attr("stroke", (d) => edgeColor(d))
      .attr("stroke-width", 1.6);

    const node = g
      .append("g")
      .selectAll("circle")
      .data(graph.ns)
      .join("circle")
      .attr("r", (d) => (d.id === selectedNodeId ? 9 : 6))
      .attr("fill", (d) => nodeColor(d))
      .attr("stroke", (d) => (d.id === selectedNodeId ? "#ef4444" : "#0f172a"))
      .attr("stroke-width", (d) => (d.id === selectedNodeId ? 2.2 : 0.8))
      .style("cursor", "pointer")
      .on("click", (_, d) => onNodeClick?.(d));

    node
      .append("title")
      .text((d) => `${d.type || "node"}: ${d.name || d.path || d.id}`);

    const sim = d3
      .forceSimulation(graph.ns)
      .force("link", d3.forceLink(graph.ls).id((d) => d.id).distance(70))
      .force("charge", d3.forceManyBody().strength(-180))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide(16));

    const drag = d3
      .drag()
      .on("start", (event, d) => {
        if (!event.active) sim.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) sim.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    node.call(drag);

    sim.on("tick", () => {
      link
        .attr("x1", (d) => d.source.x)
        .attr("y1", (d) => d.source.y)
        .attr("x2", (d) => d.target.x)
        .attr("y2", (d) => d.target.y);

      node.attr("cx", (d) => d.x).attr("cy", (d) => d.y);
    });

    // resize handling
    const ro = new ResizeObserver(() => {
      const w = containerRef.current?.clientWidth || width;
      svg.attr("width", w);
      sim.force("center", d3.forceCenter(w / 2, height / 2));
      sim.alpha(0.5).restart();
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      sim.stop();
    };
  }, [graph, height, onNodeClick, selectedNodeId]);

  return (
    <div ref={containerRef} style={{ width: "100%" }}>
      <svg ref={svgRef} style={{ width: "100%", display: "block" }} />
    </div>
  );
}