import React, { useEffect, useMemo, useRef } from "react";
import * as d3 from "d3";

// --- styling knobs ---
const BOX = { w: 170, h: 44, r: 10 };

const TYPE_BADGE = {
  process: "PROC",
  file: "FILE",
  reg_key: "REG",
  script: "SCR",
  wmi_object: "WMI",
};

function threatLevel(n) {
  // You can refine later using n.path_risk, scores, etc.
  // For now: if node path is in Temp => suspicious-ish
  const p = (n?.path || "").toLowerCase();
  if (p.includes("\\appdata\\local\\temp\\")) return "anomaly";
  return "clean";
}

function palette(level) {
  // clean=blue/gray, anomaly=yellow, isolated=red
  if (level === "isolated") {
    return { stroke: "#ef4444", glow: "#ef4444", fill: "#0b1220" };
  }
  if (level === "anomaly") {
    return { stroke: "#f59e0b", glow: "#f59e0b", fill: "#0b1220" };
  }
  return { stroke: "#38bdf8", glow: "#38bdf8", fill: "#0b1220" };
}

function nodeTitle(n) {
  const type = n?.type || "node";
  const name = n?.name || "(unnamed)";
  return `${type.toUpperCase()} • ${name}\n${n?.path || ""}`;
}

function nodePrimaryLabel(n) {
  // show readable label
  return n?.name || n?.path?.split("\\").pop() || `Node ${n?.id}`;
}

function nodeSecondaryLabel(n) {
  if (n?.type === "process") return `ID ${n.id}`;
  if (n?.type === "file") return "FILE";
  if (n?.type === "reg_key") return "REG";
  return (n?.type || "").toUpperCase();
}

export default function D3ProvenanceGraph({ nodes, edges, height = 520, onNodeClick }) {
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

    // defs: glow filter
    const defs = svg.append("defs");
    const filter = defs.append("filter").attr("id", "glow");
    filter.append("feGaussianBlur").attr("stdDeviation", "2.5").attr("result", "coloredBlur");
    const merge = filter.append("feMerge");
    merge.append("feMergeNode").attr("in", "coloredBlur");
    merge.append("feMergeNode").attr("in", "SourceGraphic");

    // zoom/pan
    const g = svg.append("g");
    svg.call(
      d3.zoom().scaleExtent([0.25, 2.5]).on("zoom", (event) => g.attr("transform", event.transform))
    );

    // Links
    const link = g
      .append("g")
      .attr("stroke-opacity", 0.55)
      .selectAll("line")
      .data(graph.ls)
      .join("line")
      .attr("stroke", "#334155")
      .attr("stroke-width", 1.3);

    // Edge labels
    const edgeLabel = g
      .append("g")
      .selectAll("text")
      .data(graph.ls)
      .join("text")
      .attr("font-size", 10)
      .attr("fill", "#94a3b8")
      .attr("font-family", "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace")
      .text((d) => d.edge_type || "");

    // Node groups (rect + text)
    const node = g
      .append("g")
      .selectAll("g")
      .data(graph.ns)
      .join("g")
      .style("cursor", "pointer")
      .on("click", (event, d) => {
        event.stopPropagation();
        onNodeClick?.(d);
      });

    // rect background
    node
      .append("rect")
      .attr("width", BOX.w)
      .attr("height", BOX.h)
      .attr("x", -BOX.w / 2)
      .attr("y", -BOX.h / 2)
      .attr("rx", BOX.r)
      .attr("fill", (d) => palette(threatLevel(d)).fill)
      .attr("stroke", (d) => palette(threatLevel(d)).stroke)
      .attr("stroke-width", 1.4)
      .attr("filter", "url(#glow)");

    // type badge
    node
      .append("text")
      .attr("x", -BOX.w / 2 + 10)
      .attr("y", -6)
      .attr("font-size", 10)
      .attr("fill", "#e2e8f0")
      .attr("font-weight", 700)
      .attr("font-family", "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace")
      .text((d) => TYPE_BADGE[d.type] || "NODE");

    // primary label
    node
      .append("text")
      .attr("x", -BOX.w / 2 + 10)
      .attr("y", 10)
      .attr("font-size", 12)
      .attr("fill", "#e2e8f0")
      .attr("font-weight", 600)
      .attr("font-family", "Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif")
      .text((d) => nodePrimaryLabel(d))
      .each(function () {
        // clip overflow by truncation
        const self = d3.select(this);
        const txt = self.text();
        if (txt.length > 22) self.text(txt.slice(0, 21) + "…");
      });

    // secondary label
    node
      .append("text")
      .attr("x", -BOX.w / 2 + 10)
      .attr("y", 27)
      .attr("font-size", 10)
      .attr("fill", "#94a3b8")
      .attr("font-family", "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace")
      .text((d) => nodeSecondaryLabel(d));

    node.append("title").text((d) => nodeTitle(d));

    // Force simulation
    const sim = d3
      .forceSimulation(graph.ns)
      .force("link", d3.forceLink(graph.ls).id((d) => d.id).distance(150))
      .force("charge", d3.forceManyBody().strength(-420))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide(BOX.w * 0.55));

    // Dragging
    const drag = d3
      .drag()
      .on("start", (event, d) => {
        if (!event.active) sim.alphaTarget(0.25).restart();
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

      node.attr("transform", (d) => `translate(${d.x},${d.y})`);

      // label at midpoint
      edgeLabel
        .attr("x", (d) => (d.source.x + d.target.x) / 2)
        .attr("y", (d) => (d.source.y + d.target.y) / 2);
    });

    // resize
    const ro = new ResizeObserver(() => {
      const w = containerRef.current?.clientWidth || width;
      svg.attr("width", w);
      sim.force("center", d3.forceCenter(w / 2, height / 2));
      sim.alpha(0.4).restart();
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      sim.stop();
    };
  }, [graph, height, onNodeClick]);

  return (
    <div ref={containerRef} style={{ width: "100%" }}>
      <svg ref={svgRef} style={{ width: "100%", display: "block" }} />
    </div>
  );
}