import type { SessionDetail } from "../api";

export type NodeState = "idle" | "active" | "done";

export const GRAPH_NODE_W = 200;
export const GRAPH_NODE_H = 72;
export const GRAPH_GAP_Y = 48;
export const GRAPH_PAD = 24;

interface LayoutNode {
  id: string;
  name: string;
  description?: string;
  type?: string;
  x: number;
  y: number;
  state: NodeState;
}

interface LayoutEdge {
  id: string;
  source: string;
  target: string;
}

/** Top-to-bottom pipeline order; ignores entry nodes outside this graph (e.g. supervisor "queen"). */
function computeVerticalOrder(
  nodes: SessionDetail["nodes"],
  edges: SessionDetail["edges"],
  entryNode?: string,
): SessionDetail["nodes"] {
  const nodeIds = new Set(nodes.map((n) => n.id));
  const entry = entryNode && nodeIds.has(entryNode) ? entryNode : undefined;
  const nodeById = new Map(nodes.map((n) => [n.id, n]));

  if (edges.length === 0) {
    return [...nodes];
  }

  const incoming = new Map<string, number>();
  const outgoing = new Map<string, string[]>();
  for (const node of nodes) {
    incoming.set(node.id, 0);
    outgoing.set(node.id, []);
  }
  for (const edge of edges) {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) continue;
    incoming.set(edge.target, (incoming.get(edge.target) || 0) + 1);
    outgoing.get(edge.source)!.push(edge.target);
  }

  const order: SessionDetail["nodes"] = [];
  const visited = new Set<string>();
  const queue: string[] = [];

  if (entry) {
    queue.push(entry);
  } else {
    for (const node of nodes) {
      if ((incoming.get(node.id) || 0) === 0) queue.push(node.id);
    }
  }

  const indegree = new Map(incoming);
  while (queue.length) {
    const id = queue.shift()!;
    if (visited.has(id)) continue;
    visited.add(id);
    const node = nodeById.get(id);
    if (node) order.push(node);

    for (const target of outgoing.get(id) || []) {
      const next = (indegree.get(target) || 0) - 1;
      indegree.set(target, next);
      if (next === 0) queue.push(target);
    }
  }

  for (const node of nodes) {
    if (!visited.has(node.id)) order.push(node);
  }

  return order;
}

export function layoutGraph(
  session: SessionDetail | null,
  nodeStates: Map<string, NodeState>,
): { nodes: LayoutNode[]; edges: LayoutEdge[]; width: number; height: number } {
  const canvasWidth = GRAPH_NODE_W + GRAPH_PAD * 2;
  const empty = { nodes: [], edges: [], width: canvasWidth, height: 320 };

  if (!session?.nodes?.length) return empty;

  const entry = session.entry_points[0]?.entry_node;
  const ordered = computeVerticalOrder(session.nodes, session.edges, entry);

  const layoutNodes: LayoutNode[] = ordered.map((node, idx) => ({
    id: node.id,
    name: node.name || node.id,
    description: node.description,
    type: (node as { type?: string }).type,
    x: GRAPH_PAD,
    y: GRAPH_PAD + idx * (GRAPH_NODE_H + GRAPH_GAP_Y),
    state: nodeStates.get(node.id) || "idle",
  }));

  const edges: LayoutEdge[] = session.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
  }));

  const height =
    ordered.length * (GRAPH_NODE_H + GRAPH_GAP_Y) - GRAPH_GAP_Y + GRAPH_PAD * 2;

  return {
    nodes: layoutNodes,
    edges,
    width: canvasWidth,
    height: Math.max(320, height),
  };
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
