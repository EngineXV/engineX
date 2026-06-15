import { useMemo } from "react";
import type { SessionDetail } from "../api";

export type NodeState = "idle" | "active" | "done";

interface LayoutNode {
  id: string;
  name: string;
  description?: string;
  x: number;
  y: number;
  state: NodeState;
}

interface LayoutEdge {
  id: string;
  source: string;
  target: string;
}

function computeLevels(
  nodes: SessionDetail["nodes"],
  edges: SessionDetail["edges"],
  entryNode?: string,
): Map<string, number> {
  const levels = new Map<string, number>();
  const incoming = new Map<string, number>();
  for (const node of nodes) incoming.set(node.id, 0);
  for (const edge of edges) {
    incoming.set(edge.target, (incoming.get(edge.target) || 0) + 1);
  }

  const roots = entryNode
    ? [entryNode]
    : nodes.filter((n) => (incoming.get(n.id) || 0) === 0).map((n) => n.id);

  const queue = [...roots];
  for (const id of roots) levels.set(id, 0);

  const out = new Map<string, string[]>();
  for (const edge of edges) {
    if (!out.has(edge.source)) out.set(edge.source, []);
    out.get(edge.source)!.push(edge.target);
  }

  while (queue.length) {
    const id = queue.shift()!;
    const level = levels.get(id) || 0;
    for (const target of out.get(id) || []) {
      const next = Math.max(level + 1, levels.get(target) ?? 0);
      levels.set(target, next);
      queue.push(target);
    }
  }

  for (const node of nodes) {
    if (!levels.has(node.id)) levels.set(node.id, 0);
  }
  return levels;
}

export function layoutGraph(
  session: SessionDetail | null,
  nodeStates: Map<string, NodeState>,
): { nodes: LayoutNode[]; edges: LayoutEdge[]; width: number; height: number } {
  if (!session) return { nodes: [], edges: [], width: 400, height: 300 };

  const entry = session.entry_points[0]?.entry_node;
  const levels = computeLevels(session.nodes, session.edges, entry);
  const byLevel = new Map<number, SessionDetail["nodes"]>();
  for (const node of session.nodes) {
    const level = levels.get(node.id) || 0;
    if (!byLevel.has(level)) byLevel.set(level, []);
    byLevel.get(level)!.push(node);
  }

  const nodeW = 160;
  const nodeH = 56;
  const gapX = 48;
  const gapY = 72;
  const pad = 24;

  const layoutNodes: LayoutNode[] = [];
  let maxRow = 0;

  for (const [level, rowNodes] of [...byLevel.entries()].sort((a, b) => a[0] - b[0])) {
    maxRow = Math.max(maxRow, rowNodes.length);
    const rowWidth = rowNodes.length * nodeW + (rowNodes.length - 1) * gapX;
    rowNodes.forEach((node, idx) => {
      layoutNodes.push({
        id: node.id,
        name: node.name || node.id,
        description: node.description,
        x: pad + idx * (nodeW + gapX) + (400 - rowWidth) / 2,
        y: pad + level * (nodeH + gapY),
        state: nodeStates.get(node.id) || "idle",
      });
    });
  }

  const pos = new Map(layoutNodes.map((n) => [n.id, n]));
  const edges: LayoutEdge[] = session.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
  }));

  const width = Math.max(400, maxRow * (nodeW + gapX) + pad * 2);
  const height = Math.max(300, (byLevel.size || 1) * (nodeH + gapY) + pad * 2);

  return { nodes: layoutNodes, edges, width, height };
}

export function edgePath(
  source: { x: number; y: number },
  target: { x: number; y: number },
  nodeW: number,
  nodeH: number,
): string {
  const sx = source.x + nodeW / 2;
  const sy = source.y + nodeH;
  const tx = target.x + nodeW / 2;
  const ty = target.y;
  const midY = (sy + ty) / 2;
  return `M ${sx} ${sy} C ${sx} ${midY}, ${tx} ${midY}, ${tx} ${ty}`;
}
