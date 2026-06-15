import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import ChatPanel, { type ChatLine } from "../components/ChatPanel";
import DashboardHeader from "../components/DashboardHeader";
import GraphView from "../components/GraphView";
import { useDashboard } from "../context/DashboardContext";
import { useSSE } from "../hooks/useSSE";
import { api, type AgentEvent, type SessionDetail } from "../api";
import type { NodeState } from "../lib/graphLayout";

function extractDelta(event: AgentEvent): string | null {
  const data = event.data || {};
  if (event.type === "client_output_delta" || event.type === "llm_text_delta") {
    const delta = data.delta ?? data.text ?? data.content;
    return typeof delta === "string" ? delta : null;
  }
  if (event.type === "client_input_requested") {
    const prompt = data.prompt ?? data.message ?? data.question;
    return typeof prompt === "string" ? prompt : "Waiting for your input…";
  }
  if (event.type === "tool_call_started") {
    const name = data.tool_name ?? data.name;
    return name ? `[tool] ${name}` : null;
  }
  if (event.type === "execution_failed") {
    const err = data.error ?? data.message;
    return typeof err === "string" ? `Error: ${err}` : "Execution failed";
  }
  if (event.type === "goal_achieved") return "Goal achieved.";
  return null;
}

export default function SessionPage() {
  const { sessionId = "" } = useParams();
  const { model, refresh } = useDashboard();
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [doneNodes, setDoneNodes] = useState<Set<string>>(new Set());
  const [waitingForInput, setWaitingForInput] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const streamNodeRef = useRef<string | null>(null);
  const lineCounter = useRef(0);

  const flushStream = useCallback(() => {
    setStreamingText((current) => {
      const text = current.trim();
      if (text) {
        lineCounter.current += 1;
        setLines((prev) => [
          ...prev,
          {
            id: `a-${lineCounter.current}`,
            role: "agent",
            text,
            timestamp: new Date().toISOString(),
          },
        ]);
      }
      streamNodeRef.current = null;
      return "";
    });
  }, []);

  const onEvent = useCallback(
    (event: AgentEvent) => {
      if (event.type === "node_loop_started" && event.node_id) {
        if (!event.graph_id || event.graph_id === "worker") {
          setActiveNode(event.node_id);
        }
      }
      if (event.type === "node_loop_completed" && event.node_id) {
        if (!event.graph_id || event.graph_id === "worker") {
          setDoneNodes((prev) => new Set(prev).add(event.node_id!));
        }
      }
      if (event.type === "execution_completed" || event.type === "execution_failed") {
        flushStream();
        setActiveNode(null);
        setWaitingForInput(false);
        void refresh();
      }
      if (event.type === "client_input_requested") {
        setWaitingForInput(true);
      }

      const delta = extractDelta(event);
      if (!delta) return;

      if (
        event.type === "client_input_requested" ||
        event.type === "tool_call_started" ||
        event.type === "execution_failed" ||
        event.type === "goal_achieved"
      ) {
        flushStream();
        lineCounter.current += 1;
        setLines((prev) => [
          ...prev,
          {
            id: `${event.type}-${lineCounter.current}`,
            role: event.type === "tool_call_started" ? "system" : "agent",
            text: delta,
            timestamp: event.timestamp,
          },
        ]);
        return;
      }

      streamNodeRef.current = event.node_id;
      setStreamingText((prev) => prev + delta);
    },
    [flushStream, refresh],
  );

  const { connected } = useSSE(sessionId, onEvent);

  useEffect(() => {
    if (!sessionId) return;
    api.getSession(sessionId)
      .then((detail) => {
        setSession(detail);
        if (detail.intro_message) {
          setLines([{ id: "intro", role: "agent", text: detail.intro_message }]);
        }
      })
      .catch((e: Error) => setError(e.message));
  }, [sessionId]);

  const graphSession = useMemo(() => {
    if (!session) return null;
    if (session.supervised && session.worker_nodes?.length) {
      return {
        ...session,
        nodes: session.worker_nodes,
        edges: session.worker_edges || [],
      };
    }
    return session;
  }, [session]);

  const nodeStates = useMemo(() => {
    const map = new Map<string, NodeState>();
    for (const node of graphSession?.nodes || []) {
      if (activeNode === node.id) map.set(node.id, "active");
      else if (doneNodes.has(node.id)) map.set(node.id, "done");
      else map.set(node.id, "idle");
    }
    return map;
  }, [graphSession, activeNode, doneNodes]);

  const send = async () => {
    const text = input.trim();
    if (!text || !sessionId) return;
    setError(null);
    setBusy(true);
    lineCounter.current += 1;
    setLines((prev) => [
      ...prev,
      { id: `u-${lineCounter.current}`, role: "user", text, timestamp: new Date().toISOString() },
    ]);
    setInput("");
    try {
      await api.sendMessage(sessionId, text);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to send message");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="session-page">
      <DashboardHeader session={session} model={model} connected={connected} />
      {error && <div className="error-banner session-error">{error}</div>}

      <div className="session-workspace">
        <section className="session-chat">
          <ChatPanel
            lines={lines}
            streamingText={streamingText}
            input={input}
            busy={busy}
            waitingForInput={waitingForInput}
            onInputChange={setInput}
            onSend={() => void send()}
          />
        </section>
        <aside className="session-graph">
          <GraphView
            session={graphSession}
            nodeStates={nodeStates}
            title={session?.supervised ? "Worker Graph" : "Agent Graph"}
          />
        </aside>
      </div>
    </div>
  );
}
