import { useNavigate } from "react-router-dom";
import { useDashboard } from "../context/DashboardContext";
import { IconChevronRight, IconSupervisor } from "../components/Icons";

export default function WelcomePage() {
  const navigate = useNavigate();
  const { supervisors, agents, model, loading, error, openAgent } = useDashboard();

  const startAgent = async (path: string) => {
    const session = await openAgent(path);
    navigate(`/session/${session.session_id}`);
  };

  return (
    <div className="welcome-page">
      <div className="welcome-inner">
        <header className="welcome-hero">
          <h1>Build. Launch. Scale.</h1>
          <p className="welcome-lead">
            Choose a department supervisor or pick a workflow agent.
            Supervisors delegate to workers and keep you in the loop.
          </p>
          <div className="welcome-meta">
            <span className="meta-chip">
              Model <strong>{model}</strong>
            </span>
            {!loading && (
              <span className="meta-chip">
                <strong>{supervisors.length}</strong> supervisor{supervisors.length === 1 ? "" : "s"} ·{" "}
                <strong>{agents.length}</strong> agent{agents.length === 1 ? "" : "s"}
              </span>
            )}
          </div>
        </header>

        {error && <div className="error-banner">{error}</div>}

        {loading ? (
          <p className="welcome-lead">Loading…</p>
        ) : (
          <>
            {supervisors.length > 0 && (
              <>
                <p className="welcome-section-label">Supervisors</p>
                <div className="welcome-supervisors">
                  {supervisors.map((supervisor) => (
                    <button
                      key={supervisor.path}
                      type="button"
                      className="welcome-supervisor-card"
                      onClick={() => void startAgent(supervisor.path)}
                    >
                      <span className="welcome-supervisor-avatar">
                        {(supervisor.supervisor_name || supervisor.name).charAt(0).toUpperCase()}
                      </span>
                      <span className="welcome-supervisor-body">
                        <strong>{supervisor.supervisor_name || supervisor.name}</strong>
                        <small>{supervisor.department}</small>
                        <span className="welcome-supervisor-role">{supervisor.role_title}</span>
                      </span>
                      <span className="welcome-supervisor-mark"><IconSupervisor size={16} /></span>
                      <span className="card-arrow"><IconChevronRight size={18} /></span>
                    </button>
                  ))}
                </div>
              </>
            )}

            {agents.length > 0 && (
              <>
                <p className="welcome-section-label">Workflow agents</p>
                <div className="welcome-agents">
                  {agents.map((agent) => (
                    <button
                      key={agent.path}
                      type="button"
                      className="welcome-agent-card"
                      onClick={() => void startAgent(agent.path)}
                    >
                      <span className="welcome-agent-icon">
                        {agent.name.charAt(0).toUpperCase()}
                      </span>
                      <span>
                        <strong>{agent.name}</strong>
                        <small>{agent.description || `${agent.node_count} workflow nodes`}</small>
                      </span>
                      <span className="card-arrow"><IconChevronRight size={18} /></span>
                    </button>
                  ))}
                </div>
              </>
            )}

            {supervisors.length === 0 && agents.length === 0 && (
              <div className="welcome-empty">
                <p>No agents found in <code>examples/templates</code> or <code>exports</code>.</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
