import React, { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";

// --- SOC Aesthetics ---
const BOX = { w: 200, h: 60, r: 10 };
const COLORS = {
  bg: "#0f172a",
  root: "#f59e0b",
  process: "#3b82f6",
  file: "#64748b",
  alert: "#ef4444",
  line: "#334155",
  text: "#f8fafc",
  subtext: "#94a3b8"
};

// SVG Icons as paths
const ICONS = {
  process: "M10.5 8a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0ZM15.434 6.738a.75.75 0 0 0-1.137-.843 3.502 3.502 0 0 1-5.69-.373.75.75 0 0 0-1.214.002 3.502 3.502 0 0 1-5.69.37.75.75 0 0 0-1.137.843 3.502 3.502 0 0 1 .37 5.69.75.75 0 0 0 .843 1.137 3.502 3.502 0 0 1 5.69.373.75.75 0 0 0 1.214-.002 3.502 3.502 0 0 1 5.69-.37.75.75 0 0 0 1.137-.843 3.502 3.502 0 0 1-.37-5.69Z",
  file: "M4.5 2.25a.75.75 0 0 0-1.5 0v15.5a.75.75 0 0 0 1.5 0V2.25Z M13.5 13H5.25v1.5h8.25V13ZM16.5 10H5.25v1.5h11.25V10ZM16.5 7H5.25v1.5h11.25V7Z",
  alert: "M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z"
};

export default function D3ProvenanceGraph({ nodes, edges, height = 500, onNodeClick, selectedNodeId }) {
  const containerRef = useRef(null);
  const svgRef = useRef(null);
  const [zoomLevel, setZoomLevel] = useState(1);

  const graphData = useMemo(() => {
    if (!nodes || nodes.length === 0) return { ns: [], ls: [] };
    const ns = nodes.map(n => ({ ...n }));
    const nodeMap = new Map(ns.map(n => [n.id, n]));
    const ls = edges
      .filter(e => nodeMap.has(e.source_id) && nodeMap.has(e.target_id))
      .map(e => ({ ...e, source: e.source_id, target: e.target_id }));

    // Level-calculation (Horizontal Depth)
    const levels = new Map();
    ns.forEach(n => levels.set(n.id, 0));
    for (let i = 0; i < 5; i++) {
      ls.forEach(e => {
        const sL = levels.get(e.source_id);
        const tL = levels.get(e.target_id);
        if (tL <= sL) levels.set(e.target_id, sL + 1);
      });
    }

    // Identify Root (Patient Zero)
    const sourceIds = new Set(ls.map(l => l.source_id));
    const targetIds = new Set(ls.map(l => l.target_id));
    ns.forEach(n => {
      n.isRoot = !targetIds.has(n.id) && sourceIds.has(n.id);
    });

    return { ns, ls, levels };
  }, [nodes, edges]);

  useEffect(() => {
    if (!containerRef.current || !svgRef.current || graphData.ns.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();
    const width = containerRef.current.clientWidth || 900;
    
    const g = svg.append("g");
    const zoom = d3.zoom()
      .scaleExtent([0.1, 3])
      .on("zoom", (e) => {
        g.attr("transform", e.transform);
        setZoomLevel(e.transform.k);
      });
    svg.call(zoom);

    // Compact Layout (SOC-Ready)
    const stepX = 180;
    const stepY = 100;
    const nodesByLevel = d3.group(graphData.ns, n => graphData.levels.get(n.id));
    
    graphData.ns.forEach(n => {
      const level = graphData.levels.get(n.id);
      const levelNodes = nodesByLevel.get(level);
      const idx = levelNodes.indexOf(n);
      n.x = 80 + (level * stepX);
      n.y = (height / 2) - ((levelNodes.length * stepY) / 2) + (idx * stepY) + (stepY / 2);
    });

    // Links (Curved Path - Tighter)
    const linkGroup = g.append("g")
      .selectAll("g")
      .data(graphData.ls)
      .join("g");

    linkGroup.append("path")
      .attr("d", d => {
        const s = graphData.ns.find(n => n.id === d.source_id);
        const t = graphData.ns.find(n => n.id === d.target_id);
        const linkGen = d3.linkHorizontal().x(l => l.x).y(l => l.y);
        return linkGen({ source: { x: s.x + BOX.w / 2, y: s.y }, target: { x: t.x - BOX.w / 2, y: t.y } });
      })
      .attr("fill", "none")
      .attr("stroke", d => (d.anomaly_score > 0.6 ? COLORS.alert : COLORS.line))
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0.4);

    // Link Labels (The "Story")
    linkGroup.append("text")
      .attr("font-size", 7)
      .attr("font-weight", 900)
      .attr("text-anchor", "middle")
      .attr("dy", -5)
      .attr("fill", d => (d.anomaly_score > 0.6 ? COLORS.alert : COLORS.subtext))
      .attr("letter-spacing", "0.1em")
      .append("textPath")
      .attr("xlink:href", (d, i) => `#linkPath-${i}`)
      .attr("startOffset", "50%")
      .text(d => d.edge_type?.toUpperCase() || "RELATION");
    
    // Hidden paths for text orientation
    linkGroup.selectAll("path")
      .attr("id", (d, i) => `linkPath-${i}`);

    // Nodes
    const node = g.append("g")
      .selectAll("g")
      .data(graphData.ns)
      .join("g")
      .attr("transform", d => `translate(${d.x},${d.y})`)
      .on("click", (e, d) => { e.stopPropagation(); onNodeClick?.(d); })
      .style("cursor", "pointer");

    node.each(function(d) {
      const el = d3.select(this);
      const isSelected = d.id === selectedNodeId;
      const themeColor = d.isRoot ? COLORS.root : (d.type === "process" ? COLORS.process : COLORS.file);
      const isCritical = d.anomaly_score > 0.7;

      // Card Background
      el.append("rect")
        .attr("width", BOX.w)
        .attr("height", BOX.h)
        .attr("x", -BOX.w / 2)
        .attr("y", -BOX.h / 2)
        .attr("rx", 8)
        .attr("fill", "#0f172a")
        .attr("stroke", isSelected ? "#fff" : COLORS.line)
        .attr("stroke-width", isSelected ? 2 : 1)
        .style("filter", isCritical ? `drop-shadow(0 0 10px ${COLORS.alert})` : null);

      // Left Accent Bar (Professional SOC style)
      el.append("rect")
        .attr("width", 6)
        .attr("height", BOX.h - 16)
        .attr("x", -BOX.w / 2 + 6)
        .attr("y", -BOX.h / 2 + 8)
        .attr("rx", 3)
        .attr("fill", isCritical ? COLORS.alert : themeColor);

      // Icon Container
      const iconPath = isCritical ? ICONS.alert : (d.type === "process" ? ICONS.process : ICONS.file);
      el.append("path")
        .attr("d", iconPath)
        .attr("transform", `translate(${-BOX.w / 2 + 18}, -10) scale(0.8)`)
        .attr("fill", isCritical ? COLORS.alert : themeColor);

      // Labels (High Clarity)
      el.append("text")
        .attr("x", -BOX.w / 2 + 42)
        .attr("y", -4)
        .attr("font-size", 11)
        .attr("font-weight", 900)
        .attr("fill", COLORS.text)
        .text(d.name || d.path?.split("\\").pop() || d.id)
        .each(function() {
          const self = d3.select(this);
          if (self.text().length > 20) self.text(self.text().slice(0, 18) + "...");
        });

      el.append("text")
        .attr("x", -BOX.w / 2 + 42)
        .attr("y", 12)
        .attr("font-size", 8)
        .attr("font-weight", 700)
        .attr("fill", COLORS.subtext)
        .attr("font-family", "Monaco, Consolas, monospace")
        .text(d.type === "process" ? (d.pid ? `PROCESS: PID ${d.pid}` : `ROOT PROCESS`) : `FILE: ${d.hash_sha256?.substring(0,8) || "NO HASH"}`);
        
      if (d.isRoot) {
        el.append("circle")
          .attr("cx", BOX.w / 2 - 15)
          .attr("cy", -BOX.h / 2 + 15)
          .attr("r", 4)
          .attr("fill", COLORS.root)
          .append("animate")
          .attr("attributeName", "opacity")
          .attr("values", "1;0.2;1")
          .attr("dur", "2s")
          .attr("repeatCount", "indefinite");
      }
    });

    // Fit View
    svg.call(zoom.transform, d3.zoomIdentity.translate(50, 0).scale(0.8));
  }, [graphData, height, onNodeClick, selectedNodeId]);

  const focusRoot = () => {
    if (!containerRef.current || !svgRef.current || graphData.ns.length === 0) return;
    const svg = d3.select(svgRef.current);
    const root = graphData.ns.find(n => n.isRoot) || graphData.ns[0];
    const width = containerRef.current.clientWidth || 900;
    
    const transform = d3.zoomIdentity
      .translate(width / 3, height / 2)
      .scale(0.9)
      .translate(-root.x, -root.y);
      
    svg.transition().duration(750).call(d3.zoom().on("zoom", (e) => d3.select(svgRef.current).select("g").attr("transform", e.transform)).transform, transform);
  };

  useEffect(() => {
    if (graphData.ns.length > 0) {
      setTimeout(focusRoot, 100);
    }
  }, [graphData.ns.length]);

  return (
    <div ref={containerRef} className="w-full h-full min-h-[500px] relative bg-[#0f172a] rounded-2xl overflow-hidden border border-slate-800 shadow-2xl">
      <svg ref={svgRef} className="w-full h-full" />
      
      {/* Control HUD */}
      <div className="absolute top-4 left-4 flex gap-2">
         <button 
           onClick={focusRoot}
           className="bg-slate-900/80 backdrop-blur-md border border-slate-700 hover:border-amber-500 text-slate-400 hover:text-amber-500 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest transition-all"
         >
           Focus Patient 0
         </button>
      </div>

      {/* Risk Flow Legend */}
      <div className="absolute bottom-6 right-6 flex items-center gap-6 bg-slate-900/90 backdrop-blur-md px-4 py-2 rounded-xl border border-white/5 pointer-events-none">
          <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500">
             <div className="w-2 h-2 rounded-full bg-blue-500"></div> PROCESS
          </div>
          <div className="flex items-center gap-2 text-[10px] font-bold text-slate-500">
             <div className="w-2 h-2 rounded-full bg-slate-500"></div> FILE
          </div>
          <div className="flex items-center gap-2 text-[10px] font-bold text-amber-500">
             <div className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse"></div> PATIENT ZERO
          </div>
          <div className="flex items-center gap-2 text-[10px] font-bold text-rose-500">
             <div className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_red]"></div> THREAT
          </div>
      </div>
    </div>
  );
}
