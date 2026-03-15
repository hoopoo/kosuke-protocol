declare module "react-force-graph-2d" {
  interface GraphData {
    nodes: NodeObject[];
    links: LinkObject[];
  }

  interface NodeObject {
    id?: string | number;
    x?: number;
    y?: number;
    vx?: number;
    vy?: number;
    fx?: number;
    fy?: number;
    [key: string]: unknown;
  }

  interface LinkObject {
    source?: string | number | NodeObject;
    target?: string | number | NodeObject;
    [key: string]: unknown;
  }

  interface ForceGraphProps {
    graphData?: GraphData;
    width?: number;
    height?: number;
    backgroundColor?: string;
    nodeLabel?: string | ((node: NodeObject) => string);
    nodeColor?: string | ((node: NodeObject) => string);
    nodeVal?: number | string | ((node: NodeObject) => number);
    nodeRelSize?: number;
    nodeCanvasObject?: (
      node: NodeObject,
      ctx: CanvasRenderingContext2D,
      globalScale: number
    ) => void;
    nodeCanvasObjectMode?: string | ((node: NodeObject) => string);
    linkColor?: string | ((link: LinkObject) => string);
    linkWidth?: number | ((link: LinkObject) => number);
    linkLineDash?: number[] | ((link: LinkObject) => number[]);
    linkDirectionalParticles?: number | ((link: LinkObject) => number);
    linkDirectionalParticleWidth?: number | ((link: LinkObject) => number);
    linkDirectionalParticleColor?: string | ((link: LinkObject) => string);
    linkCanvasObject?: (
      link: LinkObject,
      ctx: CanvasRenderingContext2D,
      globalScale: number
    ) => void;
    linkCanvasObjectMode?: string | ((link: LinkObject) => string);
    onNodeClick?: (node: NodeObject, event: MouseEvent) => void;
    onNodeHover?: (node: NodeObject | null, prevNode: NodeObject | null) => void;
    onLinkClick?: (link: LinkObject, event: MouseEvent) => void;
    onLinkHover?: (link: LinkObject | null, prevLink: LinkObject | null) => void;
    cooldownTicks?: number;
    cooldownTime?: number;
    d3AlphaDecay?: number;
    d3VelocityDecay?: number;
    warmupTicks?: number;
    onEngineStop?: () => void;
    ref?: React.Ref<ForceGraphMethods>;
  }

  interface ForceGraphMethods {
    d3Force: (forceName: string, force?: unknown) => unknown;
    d3ReheatSimulation: () => void;
    centerAt: (x?: number, y?: number, ms?: number) => void;
    zoom: (scale?: number, ms?: number) => void;
  }

  const ForceGraph2D: React.FC<ForceGraphProps>;
  export default ForceGraph2D;
  export type { GraphData, NodeObject, LinkObject, ForceGraphProps, ForceGraphMethods };
}
