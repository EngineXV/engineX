import { layoutGraph, edgePath, type NodeState } from "../lib/graphLayout";
import type { SessionDetail } from "../api";

interface GraphViewProps {
  session: SessionDetail | null;
  nodeStates: Map<string, NodeState>;
  title?: string;
}

export default function GraphView({ session, nodeStates, title = "Agent Graph" }: GraphViewProps) {
  const { nodes, edges, width, height } = layoutGraph(session, nodeStates);
  const pos = new Map(nodes.map((n) => [n.id, n]));
  const nodeW = 160;
  const nodeH = 56;

  return (
    <div className="graph-view">
      <div className="graph-view-header">
        <span>{title}</span>
        <span className="graph-legend">
          <span className="legend-item"><i className="dot idle" /> idle</span>
          <span className="legend-item"><i className="dot active" /> running</span>
          <span className="legend-item"><i className="dot done" /> done</span>
        </span>
      </div>
      <div className="graph-canvas-wrap">
        <svg viewBox={`0 0 ${width} ${height}`} className="graph-canvas">
          {edges.map((edge) => {
            const s = pos.get(edge.source);
            const t = pos.get(edge.target);
            if (!s || !t) return null;
            return (
              <path
                key={edge.id}
                d={edgePath(s, t, nodeW, nodeH)}
                className="graph-edge"
                markerEnd="url(#arrow)"
              />
            );
          })}
          <defs>
            <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" className="graph-arrow" />
            </marker>
          </defs>
          {nodes.map((node) => (
            <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
              <rect
                width={nodeW}
                height={nodeH}
                rx="10"
                className={`graph-node-box ${node.state}`}
              />
              <text x={nodeW / 2} y={22} textAnchor="middle" className="graph-node-title">
                {node.name}
              </text>
              {node.description && (
                <text x={nodeW / 2} y={40} textAnchor="middle" className="graph-node-desc">
                  {node.description.length > 22
                    ? `${node.description.slice(0, 22)}…`
                    : node.description}
                </text>
              )}
            </g>
          ))}
        </svg>
      </div>
    </div>
  );
}
