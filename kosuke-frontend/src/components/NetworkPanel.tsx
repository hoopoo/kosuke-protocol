import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { NodeObject, LinkObject } from "react-force-graph-2d";
import {
  api,
  type NetworkNode,
  type NetworkEdge,
  type NetworkMetrics,
} from "@/lib/api";
import { Network, RefreshCw, Compass, X } from "lucide-react";

// Domain → color mapping
const DOMAIN_COLORS: Record<string, string> = {
  technology: "#3b82f6", // blue
  philosophy: "#a855f7", // purple
  body: "#f97316", // orange
  urban: "#14b8a6", // teal
  culture: "#ec4899", // pink
  art: "#10b981", // green (emerald)
  science: "#06b6d4", // cyan
  nature: "#22c55e", // green
  politics: "#ef4444", // red
  economics: "#eab308", // yellow
  psychology: "#8b5cf6", // violet
  literature: "#d946ef", // fuchsia
  music: "#f59e0b", // amber
  spirituality: "#6366f1", // indigo
  mathematics: "#0ea5e9", // sky
};

const DEFAULT_NODE_COLOR = "#71717a"; // zinc-500

// Edge relation → style
const EDGE_STYLES: Record<
  string,
  { color: string; dash: number[] | null; width: number }
> = {
  fluke: { color: "#f59e0b", dash: null, width: 2 }, // glowing orange
  semantic_similarity: { color: "#52525b", dash: null, width: 0.5 }, // thin gray
  reflection_link: { color: "#e4e4e7", dash: [4, 4], width: 1 }, // dotted white
  domain_crossing: { color: "#a855f7", dash: null, width: 1.5 }, // bright purple
};

const DEFAULT_EDGE_STYLE = { color: "#3f3f46", dash: null, width: 0.5 };

interface GraphNode extends NodeObject {
  id: string;
  text: string;
  domain: string | null;
  type: string;
  is_boundary: boolean;
  degree: number;
}

interface GraphLink extends LinkObject {
  source: string;
  target: string;
  weight: number;
  relation: string;
}

interface Props {
  fragmentCount: number;
}

export function NetworkPanel({ fragmentCount }: Props) {
  const [nodes, setNodes] = useState<NetworkNode[]>([]);
  const [edges, setEdges] = useState<NetworkEdge[]>([]);
  const [metrics, setMetrics] = useState<NetworkMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [discoveryMode, setDiscoveryMode] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  const loadNetwork = useCallback(async () => {
    setLoading(true);
    try {
      const [networkData, metricsData] = await Promise.all([
        api.getNetwork(),
        api.getNetworkMetrics(),
      ]);
      setNodes(networkData.nodes);
      setEdges(networkData.edges);
      setMetrics(metricsData);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNetwork();
  }, [loadNetwork]);

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, []);

  const handleGenerateEdges = async () => {
    setGenerating(true);
    try {
      await api.generateSemanticEdges();
      await loadNetwork();
    } catch {
      /* ignore */
    } finally {
      setGenerating(false);
    }
  };

  // Compute degree per node for sizing
  const degreeMap = useMemo(() => {
    const map: Record<string, number> = {};
    for (const edge of edges) {
      map[edge.source] = (map[edge.source] || 0) + 1;
      map[edge.target] = (map[edge.target] || 0) + 1;
    }
    return map;
  }, [edges]);

  // Build graph data for ForceGraph2D
  const graphData = useMemo(() => {
    const graphNodes: GraphNode[] = nodes.map((n) => ({
      id: n.id,
      text: n.text,
      domain: n.domain,
      type: n.type,
      is_boundary: n.is_boundary,
      degree: degreeMap[n.id] || 0,
    }));

    const graphLinks: GraphLink[] = edges.map((e) => ({
      source: e.source,
      target: e.target,
      weight: e.weight,
      relation: e.relation,
    }));

    return { nodes: graphNodes, links: graphLinks };
  }, [nodes, edges, degreeMap]);

  // Discovery mode: find interesting nodes
  const discoveryNodes = useMemo(() => {
    if (!discoveryMode) return new Set<string>();
    const interesting = new Set<string>();

    for (const node of graphData.nodes) {
      // Boundary fragments
      if (node.is_boundary) interesting.add(node.id);
      // High degree nodes (top 20%)
      const degrees = graphData.nodes.map((n) => n.degree);
      const threshold = degrees.sort((a, b) => b - a)[
        Math.max(0, Math.floor(degrees.length * 0.2) - 1)
      ];
      if (threshold !== undefined && node.degree >= threshold && node.degree > 0) {
        interesting.add(node.id);
      }
    }

    return interesting;
  }, [discoveryMode, graphData.nodes]);

  // Node rendering
  const nodeCanvasObject = useCallback(
    (node: NodeObject, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const gNode = node as GraphNode;
      const size = Math.max(3, 2 + (gNode.degree || 0) * 0.8);
      const x = node.x || 0;
      const y = node.y || 0;

      const color =
        gNode.domain && DOMAIN_COLORS[gNode.domain]
          ? DOMAIN_COLORS[gNode.domain]
          : DEFAULT_NODE_COLOR;

      // Discovery mode glow
      if (discoveryMode && discoveryNodes.has(gNode.id)) {
        ctx.beginPath();
        ctx.arc(x, y, size + 4, 0, 2 * Math.PI);
        ctx.fillStyle = "rgba(245, 158, 11, 0.15)";
        ctx.fill();
      }

      // Boundary fragment: gold ring
      if (gNode.is_boundary) {
        ctx.beginPath();
        ctx.arc(x, y, size + 2, 0, 2 * Math.PI);
        ctx.strokeStyle = "#eab308";
        ctx.lineWidth = 1.5 / globalScale;
        ctx.stroke();
      }

      // Hovered node highlight
      if (hoveredNode?.id === gNode.id) {
        ctx.beginPath();
        ctx.arc(x, y, size + 3, 0, 2 * Math.PI);
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 1 / globalScale;
        ctx.stroke();
      }

      // Selected node highlight
      if (selectedNode?.id === gNode.id) {
        ctx.beginPath();
        ctx.arc(x, y, size + 3, 0, 2 * Math.PI);
        ctx.strokeStyle = "#f59e0b";
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
      }

      // Node circle
      ctx.beginPath();
      ctx.arc(x, y, size, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Label on hover or if selected
      if (
        (hoveredNode?.id === gNode.id || selectedNode?.id === gNode.id) &&
        globalScale > 1.5
      ) {
        const label = gNode.text.substring(0, 40) + (gNode.text.length > 40 ? "..." : "");
        const fontSize = 10 / globalScale;
        ctx.font = `${fontSize}px sans-serif`;
        ctx.fillStyle = "#e4e4e7";
        ctx.textAlign = "center";
        ctx.fillText(label, x, y + size + fontSize + 2);
      }
    },
    [hoveredNode, selectedNode, discoveryMode, discoveryNodes]
  );

  // Link rendering
  const linkCanvasObject = useCallback(
    (link: LinkObject, ctx: CanvasRenderingContext2D) => {
      const gLink = link as GraphLink;
      const style = EDGE_STYLES[gLink.relation] || DEFAULT_EDGE_STYLE;

      const source = link.source as NodeObject;
      const target = link.target as NodeObject;
      if (!source?.x || !source?.y || !target?.x || !target?.y) return;

      ctx.beginPath();
      ctx.strokeStyle = style.color;
      ctx.lineWidth = style.width;

      if (style.dash) {
        ctx.setLineDash(style.dash);
      } else {
        ctx.setLineDash([]);
      }

      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      ctx.stroke();
      ctx.setLineDash([]);
    },
    []
  );

  const hasData = nodes.length > 0;

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="border-b border-zinc-800 px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={loadNetwork}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          <button
            onClick={handleGenerateEdges}
            disabled={generating || fragmentCount < 2}
            className="flex items-center gap-1.5 text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-2.5 py-1.5 rounded transition-colors disabled:opacity-50"
          >
            <Network size={14} className={generating ? "animate-spin" : ""} />
            {generating ? "Scanning..." : "Discover Edges"}
          </button>
          <button
            onClick={() => setDiscoveryMode(!discoveryMode)}
            className={`flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded transition-colors ${
              discoveryMode
                ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                : "bg-zinc-800 hover:bg-zinc-700 text-zinc-400"
            }`}
          >
            <Compass size={14} />
            Explore
          </button>
        </div>

        {/* Metrics */}
        {metrics && (
          <div className="flex items-center gap-4 text-xs text-zinc-500">
            <span>
              <span className="text-zinc-300">{metrics.fragments}</span> fragments
            </span>
            <span>
              <span className="text-zinc-300">{metrics.edges}</span> edges
            </span>
            <span>
              <span className="text-zinc-300">{metrics.clusters}</span> clusters
            </span>
            <span>
              <span className="text-amber-400">{metrics.boundary_nodes}</span>{" "}
              boundary
            </span>
          </div>
        )}
      </div>

      {/* Graph + Detail panel */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Graph area */}
        <div ref={containerRef} className="flex-1 bg-zinc-950">
          {hasData ? (
            <ForceGraph2D
              graphData={graphData}
              width={dimensions.width - (selectedNode ? 320 : 0)}
              height={dimensions.height}
              backgroundColor="#09090b"
              nodeCanvasObject={nodeCanvasObject}
              nodeCanvasObjectMode={() => "replace"}
              linkCanvasObject={linkCanvasObject}
              linkCanvasObjectMode={() => "replace"}
              onNodeClick={(node) => setSelectedNode(node as GraphNode)}
              onNodeHover={(node) =>
                setHoveredNode(node ? (node as GraphNode) : null)
              }
              cooldownTicks={100}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
            />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center text-zinc-600 py-12">
              <Network size={32} className="mb-3 text-zinc-700" />
              <p className="text-sm">No network data yet</p>
              <p className="text-xs mt-1">
                {fragmentCount < 2
                  ? "Add fragments and generate flukes to build the network"
                  : 'Click "Discover Edges" to find connections between fragments'}
              </p>
            </div>
          )}
        </div>

        {/* Legend */}
        {hasData && (
          <div className="absolute bottom-4 left-4 bg-zinc-900/90 border border-zinc-800 rounded-lg p-3 space-y-2 text-xs">
            <p className="text-zinc-400 font-medium">Edges</p>
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 bg-amber-500" />
                <span className="text-zinc-500">fluke</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-px bg-zinc-600" />
                <span className="text-zinc-500">semantic</span>
              </div>
              <div className="flex items-center gap-2">
                <div
                  className="w-6 h-0"
                  style={{
                    borderTop: "1px dashed #e4e4e7",
                  }}
                />
                <span className="text-zinc-500">reflection</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-6 h-0.5 bg-purple-500" />
                <span className="text-zinc-500">domain cross</span>
              </div>
            </div>
            <p className="text-zinc-400 font-medium mt-2">Nodes</p>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full border-2 border-yellow-500 bg-transparent" />
              <span className="text-zinc-500">boundary (3+ domains)</span>
            </div>
          </div>
        )}

        {/* Detail panel */}
        {selectedNode && (
          <div className="w-80 border-l border-zinc-800 bg-zinc-900/50 overflow-y-auto shrink-0">
            <div className="p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-zinc-200">
                  Fragment Detail
                </h3>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Text */}
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                <p className="text-sm text-zinc-200 leading-relaxed italic">
                  &ldquo;{selectedNode.text}&rdquo;
                </p>
              </div>

              {/* Metadata */}
              <div className="space-y-2">
                {selectedNode.domain && (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-zinc-500">Domain:</span>
                    <span
                      className="text-xs px-2 py-0.5 rounded"
                      style={{
                        backgroundColor:
                          (DOMAIN_COLORS[selectedNode.domain] || DEFAULT_NODE_COLOR) +
                          "20",
                        color:
                          DOMAIN_COLORS[selectedNode.domain] || DEFAULT_NODE_COLOR,
                      }}
                    >
                      {selectedNode.domain}
                    </span>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500">Type:</span>
                  <span className="text-xs text-zinc-400">
                    {selectedNode.type}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-zinc-500">Connections:</span>
                  <span className="text-xs text-zinc-400">
                    {selectedNode.degree}
                  </span>
                </div>
                {selectedNode.is_boundary && (
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-yellow-500" />
                    <span className="text-xs text-yellow-400">
                      Boundary Fragment
                    </span>
                  </div>
                )}
              </div>

              {/* Connected edges */}
              <div>
                <p className="text-xs text-zinc-500 mb-2">Connections</p>
                <div className="space-y-1.5">
                  {edges
                    .filter(
                      (e) =>
                        e.source === selectedNode.id ||
                        e.target === selectedNode.id
                    )
                    .slice(0, 10)
                    .map((edge, i) => {
                      const otherId =
                        edge.source === selectedNode.id
                          ? edge.target
                          : edge.source;
                      const otherNode = nodes.find((n) => n.id === otherId);
                      const style =
                        EDGE_STYLES[edge.relation] || DEFAULT_EDGE_STYLE;
                      return (
                        <div
                          key={i}
                          className="bg-zinc-900 border border-zinc-800 rounded p-2 cursor-pointer hover:border-zinc-700 transition-colors"
                          onClick={() => {
                            const gn = graphData.nodes.find(
                              (n) => n.id === otherId
                            );
                            if (gn) setSelectedNode(gn);
                          }}
                        >
                          <p className="text-xs text-zinc-300 truncate">
                            {otherNode?.text.substring(0, 60) || otherId}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <div
                              className="w-3 h-0.5 rounded"
                              style={{ backgroundColor: style.color }}
                            />
                            <span className="text-xs text-zinc-600">
                              {edge.relation.replace("_", " ")} (
                              {edge.weight.toFixed(2)})
                            </span>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
