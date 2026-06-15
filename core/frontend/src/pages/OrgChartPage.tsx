import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDashboard } from "../context/DashboardContext";
import { IconEngine } from "../components/Icons";

import { agentLabel } from "../lib/agentLabel";

export default function OrgChartPage() {
  const navigate = useNavigate();
  const { supervisors, agents, sessions, openAgent } = useDashboard();
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null);

  const supervisorTree = useMemo(() => {
    return supervisors.map((supervisor) => ({
      supervisor,
      sessions: sessions.filter((s) => s.agent_path === supervisor.path),
    }));
  }, [supervisors, sessions]);

  const agentTree = useMemo(() => {
    return agents.map((agent) => ({
      agent,
      sessions: sessions.filter((s) => s.agent_path === agent.path),
    }));
  }, [agents, sessions]);

  const hasSplit = supervisorTree.length > 0 && agentTree.length > 0;

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
          <p>Engine → Supervisors → sessions · Workflow agents</p>
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

          {(supervisorTree.length > 0 || agentTree.length > 0) && (
            <>
              <div className="org-vline" aria-hidden />

              <div className={`org-tier${hasSplit ? " org-tier-split" : ""}`}>
                {supervisorTree.length > 0 && (
                  <div className="org-subtree">
                    <span className="org-node supervisor org-supervisor-hub">
                      <span className="org-node-icon">S</span>
                      <strong>Supervisors</strong>
                      <small>Department leads</small>
                    </span>
                    <div className="org-vline" aria-hidden />
                    <div className="org-children-row">
                      {supervisorTree.map(({ supervisor, sessions: supervisorSessions }) => (
                        <div key={supervisor.path} className="org-child-col">
                          <button
                            type="button"
                            className="org-node supervisor"
                            onClick={() => void startAgent(supervisor.path)}
                          >
                            <span className="org-node-icon">
                              {(supervisor.supervisor_name || supervisor.name).charAt(0)}
                            </span>
                            <strong>{supervisor.supervisor_name || supervisor.name}</strong>
                            <small>{supervisor.department}</small>
                          </button>
                          {supervisorSessions.length > 0 && (
                            <>
                              <div className="org-vline org-vline-short" aria-hidden />
                              <div className="org-sessions">
                                {supervisorSessions.map((session) => (
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
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {agentTree.length > 0 && (
                  <div className="org-subtree org-subtree-agents">
                    <span className="org-node org-tier-hub">
                      <span className="org-node-icon">A</span>
                      <strong>Workflow agents</strong>
                      <small>Templates & exports</small>
                    </span>
                    <div className="org-vline" aria-hidden />
                    <div className="org-children-row">
                      {agentTree.map(({ agent, sessions: agentSessions }) => (
                        <div key={agent.path} className="org-child-col">
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
                            <>
                              <div className="org-vline org-vline-short" aria-hidden />
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
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
