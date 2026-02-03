"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";

// --- Types ---

export interface FlowchartNode {
  id: string;
  label: string;
  style?: string;
}

export interface FlowchartEdge {
  from: string;
  to: string;
  label?: string;
}

export interface FlowchartSubgraph {
  id: string;
  label: string;
  nodeIds: string[];
}

export interface FlowchartData {
  type: "flowchart";
  direction: "TD" | "LR";
  nodes: FlowchartNode[];
  edges: FlowchartEdge[];
  subgraphs?: FlowchartSubgraph[];
}

// --- Layout ---

interface NodeLayout {
  id: string;
  x: number;
  y: number;
  rank: number;
  width: number;
  height: number;
}

const NODE_W = 180;
const NODE_H = 52;
const GAP_X = 40;
const GAP_Y = 60;

function computeLayout(
  nodes: FlowchartNode[],
  edges: FlowchartEdge[],
  direction: "TD" | "LR"
): { nodeLayouts: Map<string, NodeLayout>; width: number; height: number } {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  const children = new Map<string, string[]>();
  const parents = new Map<string, string[]>();

  for (const n of nodes) {
    children.set(n.id, []);
    parents.set(n.id, []);
  }
  for (const e of edges) {
    children.get(e.from)?.push(e.to);
    parents.get(e.to)?.push(e.from);
  }

  // BFS from roots to assign ranks
  const roots = nodes.filter((n) => (parents.get(n.id)?.length ?? 0) === 0);
  if (roots.length === 0 && nodes.length > 0) roots.push(nodes[0]);

  const rankMap = new Map<string, number>();
  const queue: string[] = roots.map((r) => r.id);
  for (const r of roots) rankMap.set(r.id, 0);

  while (queue.length > 0) {
    const id = queue.shift()!;
    const rank = rankMap.get(id)!;
    for (const child of children.get(id) || []) {
      const existing = rankMap.get(child);
      if (existing === undefined || existing < rank + 1) {
        rankMap.set(child, rank + 1);
        queue.push(child);
      }
    }
  }

  // Assign rank to any disconnected nodes
  for (const n of nodes) {
    if (!rankMap.has(n.id)) rankMap.set(n.id, 0);
  }

  // Group by rank
  const maxRank = Math.max(...rankMap.values(), 0);
  const ranks: string[][] = Array.from({ length: maxRank + 1 }, () => []);
  for (const n of nodes) {
    ranks[rankMap.get(n.id)!].push(n.id);
  }

  // Compute positions
  const layouts = new Map<string, NodeLayout>();
  const isVertical = direction === "TD";

  for (let r = 0; r <= maxRank; r++) {
    const group = ranks[r];
    const count = group.length;
    for (let i = 0; i < count; i++) {
      const offsetInGroup = i - (count - 1) / 2;
      let x: number, y: number;
      if (isVertical) {
        x = offsetInGroup * (NODE_W + GAP_X);
        y = r * (NODE_H + GAP_Y);
      } else {
        x = r * (NODE_W + GAP_X);
        y = offsetInGroup * (NODE_H + GAP_Y);
      }
      layouts.set(group[i], {
        id: group[i],
        x,
        y,
        rank: r,
        width: NODE_W,
        height: NODE_H,
      });
    }
  }

  // Compute bounding box, then shift so min is at 0
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const l of layouts.values()) {
    minX = Math.min(minX, l.x);
    minY = Math.min(minY, l.y);
    maxX = Math.max(maxX, l.x + l.width);
    maxY = Math.max(maxY, l.y + l.height);
  }
  for (const l of layouts.values()) {
    l.x -= minX;
    l.y -= minY;
  }

  return {
    nodeLayouts: layouts,
    width: maxX - minX,
    height: maxY - minY,
  };
}

// --- Styling ---

const NODE_STYLES: Record<string, { bg: string; border: string; text: string; hoverBg: string }> = {
  primary: {
    bg: "bg-primary-100",
    border: "border-primary-400",
    text: "text-primary-800",
    hoverBg: "hover:bg-primary-200",
  },
  step: {
    bg: "bg-blue-50",
    border: "border-blue-300",
    text: "text-blue-800",
    hoverBg: "hover:bg-blue-100",
  },
  decision: {
    bg: "bg-amber-50",
    border: "border-amber-400",
    text: "text-amber-800",
    hoverBg: "hover:bg-amber-100",
  },
  highlight: {
    bg: "bg-emerald-50",
    border: "border-emerald-400",
    text: "text-emerald-800",
    hoverBg: "hover:bg-emerald-100",
  },
  warning: {
    bg: "bg-rose-50",
    border: "border-rose-400",
    text: "text-rose-800",
    hoverBg: "hover:bg-rose-100",
  },
};

// --- Edge path ---

function edgePath(
  from: NodeLayout,
  to: NodeLayout,
  direction: "TD" | "LR"
): string {
  let sx: number, sy: number, ex: number, ey: number;
  if (direction === "TD") {
    sx = from.x + from.width / 2;
    sy = from.y + from.height;
    ex = to.x + to.width / 2;
    ey = to.y;
  } else {
    sx = from.x + from.width;
    sy = from.y + from.height / 2;
    ex = to.x;
    ey = to.y + to.height / 2;
  }
  const midX = (sx + ex) / 2;
  const midY = (sy + ey) / 2;
  if (direction === "TD") {
    return `M ${sx} ${sy} C ${sx} ${midY}, ${ex} ${midY}, ${ex} ${ey}`;
  }
  return `M ${sx} ${sy} C ${midX} ${sy}, ${midX} ${ey}, ${ex} ${ey}`;
}

// --- Arrow marker ---

function ArrowMarker() {
  return (
    <defs>
      <marker
        id="flowchart-arrow"
        viewBox="0 0 10 10"
        refX="9"
        refY="5"
        markerWidth="6"
        markerHeight="6"
        orient="auto-start-reverse"
      >
        <path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor" className="text-slate-400" />
      </marker>
    </defs>
  );
}

// --- Component ---

const PADDING = 24;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 3;
const ZOOM_STEP = 0.25;

export function InteractiveFlowchart({ data }: { data: FlowchartData }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [visible, setVisible] = useState(false);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // Zoom and pan state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });
  const [isTouchDevice, setIsTouchDevice] = useState(false);
  const pinchRef = useRef({ dist: 0, zoom: 1, midX: 0, midY: 0, panX: 0, panY: 0 });

  // Intersection observer for entry animation
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.15 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const { nodeLayouts, width, height } = useMemo(
    () => computeLayout(data.nodes, data.edges, data.direction),
    [data.nodes, data.edges, data.direction]
  );

  // Zoom handlers
  const handleZoomIn = useCallback(() => {
    setZoom((z) => Math.min(MAX_ZOOM, z + ZOOM_STEP));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom((z) => Math.max(MIN_ZOOM, z - ZOOM_STEP));
  }, []);

  const handleZoomReset = useCallback(() => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, []);

  // Wheel zoom - centered on cursor position
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const onWheel = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
      setZoom((z) => {
        const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z + delta));
        if (next !== z) {
          // Adjust pan to zoom toward cursor
          const rect = svg.getBoundingClientRect();
          const cx = (e.clientX - rect.left) / rect.width;
          const cy = (e.clientY - rect.top) / rect.height;
          const svgW = width + PADDING * 2;
          const svgH = height + PADDING * 2;
          const vwOld = svgW / z;
          const vwNew = svgW / next;
          const vhOld = svgH / z;
          const vhNew = svgH / next;
          setPan((p) => ({
            x: p.x + (vwOld - vwNew) * cx,
            y: p.y + (vhOld - vhNew) * cy,
          }));
        }
        return next;
      });
    };
    svg.addEventListener("wheel", onWheel, { passive: false });
    return () => svg.removeEventListener("wheel", onWheel);
  }, [width, height]);

  // Pan via mouse drag
  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      if (zoom <= 1) return;
      setIsPanning(true);
      panStart.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y };
      (e.target as Element).setPointerCapture?.(e.pointerId);
    },
    [zoom, pan]
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!isPanning) return;
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const svgW = width + PADDING * 2;
      const svgH = height + PADDING * 2;
      const scaleX = (svgW / zoom) / rect.width;
      const scaleY = (svgH / zoom) / rect.height;
      const dx = (e.clientX - panStart.current.x) * scaleX;
      const dy = (e.clientY - panStart.current.y) * scaleY;
      setPan({ x: panStart.current.panX - dx, y: panStart.current.panY - dy });
    },
    [isPanning, zoom, width, height]
  );

  const handlePointerUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  // Touch pinch-to-zoom and single-finger pan
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const getTouchDist = (t: TouchList) => {
      const dx = t[1].clientX - t[0].clientX;
      const dy = t[1].clientY - t[0].clientY;
      return Math.sqrt(dx * dx + dy * dy);
    };

    const onTouchStart = (e: TouchEvent) => {
      setIsTouchDevice(true);
      if (e.touches.length === 2) {
        e.preventDefault();
        const dist = getTouchDist(e.touches);
        const rect = svg.getBoundingClientRect();
        const midX = ((e.touches[0].clientX + e.touches[1].clientX) / 2 - rect.left) / rect.width;
        const midY = ((e.touches[0].clientY + e.touches[1].clientY) / 2 - rect.top) / rect.height;
        pinchRef.current = { dist, zoom, midX, midY, panX: pan.x, panY: pan.y };
      } else if (e.touches.length === 1 && zoom > 1) {
        e.preventDefault();
        setIsPanning(true);
        panStart.current = { x: e.touches[0].clientX, y: e.touches[0].clientY, panX: pan.x, panY: pan.y };
      }
    };

    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 2) {
        e.preventDefault();
        const dist = getTouchDist(e.touches);
        const scale = dist / pinchRef.current.dist;
        const nextZoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, pinchRef.current.zoom * scale));
        const svgW = width + PADDING * 2;
        const svgH = height + PADDING * 2;
        const vwOld = svgW / pinchRef.current.zoom;
        const vwNew = svgW / nextZoom;
        const vhOld = svgH / pinchRef.current.zoom;
        const vhNew = svgH / nextZoom;
        setZoom(nextZoom);
        setPan({
          x: pinchRef.current.panX + (vwOld - vwNew) * pinchRef.current.midX,
          y: pinchRef.current.panY + (vhOld - vhNew) * pinchRef.current.midY,
        });
      } else if (e.touches.length === 1 && isPanning) {
        e.preventDefault();
        const rect = svg.getBoundingClientRect();
        const svgW = width + PADDING * 2;
        const svgH = height + PADDING * 2;
        const scaleX = (svgW / zoom) / rect.width;
        const scaleY = (svgH / zoom) / rect.height;
        const dx = (e.touches[0].clientX - panStart.current.x) * scaleX;
        const dy = (e.touches[0].clientY - panStart.current.y) * scaleY;
        setPan({ x: panStart.current.panX - dx, y: panStart.current.panY - dy });
      }
    };

    const onTouchEnd = (e: TouchEvent) => {
      if (e.touches.length < 2) {
        setIsPanning(false);
      }
    };

    svg.addEventListener("touchstart", onTouchStart, { passive: false });
    svg.addEventListener("touchmove", onTouchMove, { passive: false });
    svg.addEventListener("touchend", onTouchEnd);
    return () => {
      svg.removeEventListener("touchstart", onTouchStart);
      svg.removeEventListener("touchmove", onTouchMove);
      svg.removeEventListener("touchend", onTouchEnd);
    };
  }, [zoom, pan, isPanning, width, height]);

  // Find connected edges for hover highlighting
  const connectedEdges = useCallback(
    (nodeId: string | null) => {
      if (!nodeId) return new Set<string>();
      const set = new Set<string>();
      for (const e of data.edges) {
        if (e.from === nodeId || e.to === nodeId) {
          set.add(`${e.from}-${e.to}`);
        }
      }
      return set;
    },
    [data.edges]
  );

  const connectedNodes = useCallback(
    (nodeId: string | null) => {
      if (!nodeId) return new Set<string>();
      const set = new Set<string>([nodeId]);
      for (const e of data.edges) {
        if (e.from === nodeId) set.add(e.to);
        if (e.to === nodeId) set.add(e.from);
      }
      return set;
    },
    [data.edges]
  );

  const activeEdges = connectedEdges(hoveredNode);
  const activeNodes = connectedNodes(hoveredNode);

  // Subgraph bounding boxes
  const subgraphBoxes = useMemo(() => {
    if (!data.subgraphs) return [];
    return data.subgraphs.map((sg) => {
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      for (const nid of sg.nodeIds) {
        const nl = nodeLayouts.get(nid);
        if (!nl) continue;
        minX = Math.min(minX, nl.x);
        minY = Math.min(minY, nl.y);
        maxX = Math.max(maxX, nl.x + nl.width);
        maxY = Math.max(maxY, nl.y + nl.height);
      }
      return { ...sg, minX: minX - 12, minY: minY - 28, maxX: maxX + 12, maxY: maxY + 12 };
    });
  }, [data.subgraphs, nodeLayouts]);

  const svgW = width + PADDING * 2;
  const svgH = height + PADDING * 2;

  // Compute viewBox from zoom and pan
  const vbW = svgW / zoom;
  const vbH = svgH / zoom;
  const vbX = pan.x;
  const vbY = pan.y;

  const isZoomed = zoom !== 1 || pan.x !== 0 || pan.y !== 0;

  return (
    <div
      ref={containerRef}
      className="bg-white rounded-xl border border-slate-200 p-4 overflow-hidden relative group"
    >
      {/* Zoom controls - always visible on touch, hover-reveal on desktop */}
      <div className={cn(
        "absolute top-2 right-2 z-10 flex items-center gap-1 transition-opacity duration-200",
        isTouchDevice ? "opacity-100" : "opacity-0 group-hover:opacity-100"
      )}>
        <button
          onClick={handleZoomIn}
          disabled={zoom >= MAX_ZOOM}
          className="w-7 h-7 flex items-center justify-center rounded-md bg-white border border-slate-200 text-slate-500 hover:bg-slate-50 hover:text-slate-700 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-bold shadow-sm"
          title="Zoom in (Ctrl+Scroll)"
        >
          +
        </button>
        <button
          onClick={handleZoomOut}
          disabled={zoom <= MIN_ZOOM}
          className="w-7 h-7 flex items-center justify-center rounded-md bg-white border border-slate-200 text-slate-500 hover:bg-slate-50 hover:text-slate-700 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-bold shadow-sm"
          title="Zoom out (Ctrl+Scroll)"
        >
          -
        </button>
        {isZoomed && (
          <button
            onClick={handleZoomReset}
            className="h-7 px-2 flex items-center justify-center rounded-md bg-white border border-slate-200 text-slate-500 hover:bg-slate-50 hover:text-slate-700 text-xs font-medium shadow-sm"
            title="Reset zoom"
          >
            {Math.round(zoom * 100)}%
          </button>
        )}
      </div>

      <svg
        ref={svgRef}
        viewBox={`${vbX} ${vbY} ${vbW} ${vbH}`}
        width="100%"
        className={cn("max-w-full", zoom > 1 && "cursor-grab", isPanning && "cursor-grabbing")}
        style={{ minHeight: Math.min(svgH, 500), touchAction: "none" }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      >
        <ArrowMarker />

        {/* Subgraph backgrounds */}
        {subgraphBoxes.map((sg) => (
          <g key={sg.id}>
            <rect
              x={sg.minX + PADDING}
              y={sg.minY + PADDING}
              width={sg.maxX - sg.minX}
              height={sg.maxY - sg.minY}
              rx={8}
              fill="rgb(248,250,252)"
              stroke="rgb(226,232,240)"
              strokeWidth={1}
              strokeDasharray="4 2"
            />
            <text
              x={sg.minX + PADDING + 8}
              y={sg.minY + PADDING + 16}
              fontSize={11}
              fontWeight={600}
              fill="rgb(100,116,139)"
            >
              {sg.label}
            </text>
          </g>
        ))}

        {/* Edges */}
        {data.edges.map((e, i) => {
          const from = nodeLayouts.get(e.from);
          const to = nodeLayouts.get(e.to);
          if (!from || !to) return null;
          const key = `${e.from}-${e.to}`;
          const isActive = hoveredNode === null || activeEdges.has(key);
          const rank = Math.max(from.rank, to.rank);

          return (
            <g
              key={i}
              className="transition-opacity duration-300"
              style={{
                opacity: visible ? (isActive ? 1 : 0.25) : 0,
                transitionDelay: visible ? `${rank * 120 + 60}ms` : "0ms",
              }}
            >
              <path
                d={edgePath(
                  { ...from, x: from.x + PADDING, y: from.y + PADDING },
                  { ...to, x: to.x + PADDING, y: to.y + PADDING },
                  data.direction
                )}
                fill="none"
                stroke={isActive && hoveredNode ? "rgb(139,92,246)" : "rgb(203,213,225)"}
                strokeWidth={isActive && hoveredNode ? 2 : 1.5}
                markerEnd="url(#flowchart-arrow)"
                className="transition-all duration-200"
              />
              {e.label && (
                <text
                  x={(from.x + to.x) / 2 + from.width / 2 + PADDING}
                  y={(from.y + to.y) / 2 + from.height / 2 + PADDING - 6}
                  fontSize={10}
                  fill="rgb(100,116,139)"
                  textAnchor="middle"
                  className="pointer-events-none"
                >
                  {e.label}
                </text>
              )}
            </g>
          );
        })}

        {/* Nodes */}
        {data.nodes.map((node) => {
          const nl = nodeLayouts.get(node.id);
          if (!nl) return null;
          const style = NODE_STYLES[node.style || "step"] || NODE_STYLES.step;
          const isActive = hoveredNode === null || activeNodes.has(node.id);
          const isHovered = hoveredNode === node.id;

          // Map Tailwind classes to SVG fills
          const fills: Record<string, { bg: string; border: string; text: string }> = {
            primary: { bg: "#ede9fe", border: "#a78bfa", text: "#5b21b6" },
            step: { bg: "#eff6ff", border: "#93c5fd", text: "#1e40af" },
            decision: { bg: "#fffbeb", border: "#fbbf24", text: "#92400e" },
            highlight: { bg: "#ecfdf5", border: "#34d399", text: "#065f46" },
            warning: { bg: "#fff1f2", border: "#fb7185", text: "#9f1239" },
          };
          const f = fills[node.style || "step"] || fills.step;

          // Compute text wrapping
          const maxChars = Math.floor(NODE_W / 7.5);
          const words = node.label.split(" ");
          const lines: string[] = [];
          let current = "";
          for (const w of words) {
            if (current && (current + " " + w).length > maxChars) {
              lines.push(current);
              current = w;
            } else {
              current = current ? current + " " + w : w;
            }
          }
          if (current) lines.push(current);

          const lineHeight = 14;
          const textBlockH = lines.length * lineHeight;
          const nodeH = Math.max(NODE_H, textBlockH + 20);

          return (
            <g
              key={node.id}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              className="cursor-pointer transition-all duration-300"
              style={{
                opacity: visible ? (isActive ? 1 : 0.35) : 0,
                transform: visible
                  ? "translateY(0px)"
                  : "translateY(12px)",
                transitionDelay: visible ? `${nl.rank * 120}ms` : "0ms",
              }}
            >
              <rect
                x={nl.x + PADDING}
                y={nl.y + PADDING}
                width={nl.width}
                height={nodeH}
                rx={node.style === "decision" ? 2 : 10}
                fill={isHovered ? f.border + "30" : f.bg}
                stroke={f.border}
                strokeWidth={isHovered ? 2.5 : 1.5}
                className="transition-all duration-200"
              />
              {lines.map((line, li) => (
                <text
                  key={li}
                  x={nl.x + nl.width / 2 + PADDING}
                  y={nl.y + nodeH / 2 + PADDING + (li - (lines.length - 1) / 2) * lineHeight}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={12}
                  fontWeight={node.style === "primary" ? 700 : 500}
                  fill={f.text}
                  className="pointer-events-none select-none"
                >
                  {line}
                </text>
              ))}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
