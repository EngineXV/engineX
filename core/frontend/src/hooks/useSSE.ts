import { useEffect, useRef, useState } from "react";
import type { AgentEvent } from "./api";

export function useSSE(
  sessionId: string | null,
  onEvent: (event: AgentEvent) => void,
) {
  const [connected, setConnected] = useState(false);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!sessionId) return;

    const es = new EventSource(`/api/sessions/${sessionId}/events`);
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      try {
        onEventRef.current(JSON.parse(e.data) as AgentEvent);
      } catch {
        // keepalive
      }
    };
    return () => {
      es.close();
      setConnected(false);
    };
  }, [sessionId]);

  return { connected };
}
