import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type AgentEntry, type SessionSummary } from "../api";

interface DashboardState {
  agents: AgentEntry[];
  supervisors: AgentEntry[];
  sessions: SessionSummary[];
  model: string;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  openAgent: (agentPath: string) => Promise<SessionSummary>;
}

const DashboardContext = createContext<DashboardState | null>(null);

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [agents, setAgents] = useState<AgentEntry[]>([]);
  const [supervisors, setSupervisors] = useState<AgentEntry[]>([]);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [model, setModel] = useState("—");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [discover, sessionList, config] = await Promise.all([
        api.discover(),
        api.listSessions(),
        api.getConfig(),
      ]);
      setAgents([...discover.templates, ...discover.exports]);
      setSupervisors(
        (discover.supervisors || [])
          .filter((entry) => entry.node_count > 0 || entry.supervisor_name || entry.supervisor),
      );
      setSessions(sessionList.sessions);
      setModel(config.model);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 15000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const openAgent = useCallback(async (agentPath: string) => {
    const session = await api.createSession(agentPath);
    await refresh();
    return session;
  }, [refresh]);

  const value = useMemo(
    () => ({ agents, supervisors, sessions, model, loading, error, refresh, openAgent }),
    [agents, supervisors, sessions, model, loading, error, refresh, openAgent],
  );

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard() {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboard must be used within DashboardProvider");
  return ctx;
}
