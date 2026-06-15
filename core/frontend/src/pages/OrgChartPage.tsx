import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDashboard } from "../context/DashboardContext";
import { IconEngine } from "../components/Icons";

import { agentLabel } from "../lib/agentLabel";

export default function OrgChartPage() {
  const navigate = useNavigate();
  const { queens, agents, sessions, openAgent } = useDashboard();
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);

  const queenTree = useMemo(() => {
    return queens.map((queen) => ({
      queen,
      sessions: sessions.filter((s) => s.agent_path === queen.path),
    }));
  }, [queens, sessions]);

  const tree = useMemo(() => {
    return agents.map((agent) => ({
      agent,
      sessions: sessions.filter((s) => s.agent_path === agent.path),
    }));
  }, [agents, sessions]);

  const onMouseDown = (e: React.MouseEvent) => {
    drag.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y };
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (!drag.current) return;
    setOffset({
      x: drag.current.ox + (e.clientX - drag.current.x),
      y: drag.current.oy + (e.clientY - drag.current.y),
    });
  };

  const onMouseUp = () => {
    drag.current = null;
  };

  const startAgent = async (path: string) => {
    const session = await openAgent(path);
    navigate(`/session/${session.session_id}`);
  };

  return (
    <div className="feature-page org-page">
      <header className="feature-header">
        <div>
          <h1>Org Chart</h1>
          <p>Engine → Queen Bees (by department) → workflow agents → live sessions.</p>
        </div>
        <div className="feature-header-actions">
          <button type="button" className="btn-secondary" onClick={() => setScale((s) => Math.min(1.6, s + 0.1))}>
            Zoom +
          </button>
          <button type="button" className="btn-secondary" onClick={() => setScale((s) => Math.max(0.6, s - 0.1))}>
            Zoom −
          </button>
        </div>
      </header>

      <div
        className="org-canvas"
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
      >
        <div
          className="org-tree"
          style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})` }}
        >
          <button type="button" className="org-node root" onClick={() => navigate("/")}>
            <span className="org-node-icon"><IconEngine size={18} /></span>
            <strong>Engine</strong>
            <small>Runtime hub</small>
          </button>

          <div className="org-branches">
            {queenTree.length > 0 && (
              <div className="org-branch org-queen-branch">
                <span className="org-node queen org-queen-hub">
                  <span className="org-node-icon">Q</span>
                  <strong>Queen Bees</strong>
                  <small>Department supervisors</small>
                </span>
                <div className="org-queen-grid">
                  {queenTree.map(({ queen, sessions: queenSessions }) => (
                    <div key={queen.path} className="org-queen-col">
                      <button
                        type="button"
                        className="org-node queen"
                        onClick={() => void startAgent(queen.path)}
                      >
                        <span className="org-node-icon">
                          {(queen.queen_name || queen.name).charAt(0)}
                        </span>
                        <strong>{queen.queen_name || queen.name}</strong>
                        <small>{queen.department}</small>
                      </button>
                      {queenSessions.length > 0 && (
                        <div className="org-sessions">
                          {queenSessions.map((session) => (
                            <button
                              key={session.session_id}
                              type="button"
                              className="org-node session"
                              onClick={() => navigate(`/session/${session.session_id}`)}
                            >
                              <span className={`status-dot ${session.current_exec_id ? "on" : "off"}`} />
                              <strong>{session.session_id.slice(0, 8)}…</strong>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tree.map(({ agent, sessions: agentSessions }) => (
              <div key={agent.path} className="org-branch">
                <button
                  type="button"
                  className="org-node agent"
                  onClick={() => void startAgent(agent.path)}
                >
                  <span className="org-node-icon">{agentLabel(agent.name).charAt(0)}</span>
                  <strong>{agentLabel(agent.name)}</strong>
                  <small>{agent.node_count} nodes · {agent.tool_count} tools</small>
                </button>

                {agentSessions.length > 0 && (
                  <div className="org-sessions">
                    {agentSessions.map((session) => (
                      <button
                        key={session.session_id}
                        type="button"
                        className="org-node session"
                        onClick={() => navigate(`/session/${session.session_id}`)}
                      >
                        <span className={`status-dot ${session.current_exec_id ? "on" : "off"}`} />
                        <strong>{session.session_id.slice(0, 8)}…</strong>
                        <small>{session.current_exec_id ? "Running" : "Idle"}</small>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
