import {
  GRAPH_NODE_H,
  GRAPH_NODE_W,
  edgePath,
  layoutGraph,
  type NodeState,
} from "../lib/graphLayout";
import type { SessionDetail } from "../api";

interface GraphViewProps {
  session: SessionDetail | null;
  nodeStates: Map<string, NodeState>;
  title?: string;
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

export default function GraphView({ session, nodeStates, title = "Agent Graph" }: GraphViewProps) {
  const { nodes, edges, width, height } = layoutGraph(session, nodeStates);
  const pos = new Map(nodes.map((n) => [n.id, n]));
  const nodeCount = session?.nodes?.length ?? 0;

  return (
    <div className="graph-view">
      <div className="graph-view-header">
        <div className="graph-view-title">
          <span>{title}</span>
          {nodeCount > 0 && (
            <span className="graph-view-subtitle">
              {nodeCount} node{nodeCount === 1 ? "" : "s"}
            </span>
          )}
        </div>
        <span className="graph-legend">
          <span className="legend-item">
            <i className="dot idle" /> idle
          </span>
          <span className="legend-item">
            <i className="dot active" /> running
          </span>
          <span className="legend-item">
            <i className="dot done" /> done
          </span>
        </span>
      </div>
      <div className="graph-canvas-wrap">
        {nodes.length === 0 ? (
          <div className="graph-empty">No graph nodes loaded yet.</div>
        ) : (
          <svg
            viewBox={`0 0 ${width} ${height}`}
            width="100%"
            height={height}
            preserveAspectRatio="xMidYMin meet"
            className="graph-canvas"
            role="img"
            aria-label={`${title} with ${nodes.length} nodes`}
          >
            <defs>
              <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="4" orient="auto">
                <path d="M0,0 L8,4 L0,8 Z" className="graph-arrow" />
              </marker>
              <filter id="node-shadow" x="-20%" y="-20%" width="140%" height="140%">
                <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.35" />
              </filter>
            </defs>
            {edges.map((edge) => {
              const s = pos.get(edge.source);
              const t = pos.get(edge.target);
              if (!s || !t) return null;
              return (
                <path
                  key={edge.id}
                  d={edgePath(s, t, GRAPH_NODE_W, GRAPH_NODE_H)}
                  className="graph-edge"
                  markerEnd="url(#arrow)"
                />
              );
            })}
            {nodes.map((node) => (
              <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
                <rect
                  width={GRAPH_NODE_W}
                  height={GRAPH_NODE_H}
                  rx="12"
                  className={`graph-node-box ${node.state}`}
                  filter="url(#node-shadow)"
                />
                {node.state === "active" && (
                  <rect
                    width={GRAPH_NODE_W}
                    height={GRAPH_NODE_H}
                    rx="12"
                    className="graph-node-glow"
                  />
                )}
                {node.type && (
                  <text x={12} y={18} className="graph-node-type">
                    {truncate(node.type.replace(/_/g, " "), 14)}
                  </text>
                )}
                <text
                  x={GRAPH_NODE_W / 2}
                  y={node.type ? 38 : 30}
                  textAnchor="middle"
                  className="graph-node-title"
                >
                  {truncate(node.name, 22)}
                </text>
                {node.description && (
                  <text
                    x={GRAPH_NODE_W / 2}
                    y={node.type ? 56 : 48}
                    textAnchor="middle"
                    className="graph-node-desc"
                  >
                    {truncate(node.description, 28)}
                  </text>
                )}
              </g>
            ))}
          </svg>
        )}
      </div>
    </div>
  );
}
