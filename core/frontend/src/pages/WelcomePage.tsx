import { useNavigate } from "react-router-dom";
import { useDashboard } from "../context/DashboardContext";
import { IconChevronRight, IconCrown } from "../components/Icons";

export default function WelcomePage() {
  const navigate = useNavigate();
  const { queens, agents, model, loading, error, openAgent } = useDashboard();

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
            Choose a Queen Bee for your department or pick a workflow agent.
            Queens supervise workers and keep you in the loop.
          </p>
          <div className="welcome-meta">
            <span className="meta-chip">
              Model <strong>{model}</strong>
            </span>
            {!loading && (
              <span className="meta-chip">
                <strong>{queens.length}</strong> queen{queens.length === 1 ? "" : "s"} ·{" "}
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
            {queens.length > 0 && (
              <>
                <p className="welcome-section-label">Queen Bees</p>
                <div className="welcome-queens">
                  {queens.map((queen) => (
                    <button
                      key={queen.path}
                      type="button"
                      className="welcome-queen-card"
                      onClick={() => void startAgent(queen.path)}
                    >
                      <span className="welcome-queen-avatar">
                        {(queen.queen_name || queen.name).charAt(0).toUpperCase()}
                      </span>
                      <span className="welcome-queen-body">
                        <strong>{queen.queen_name || queen.name}</strong>
                        <small>{queen.department}</small>
                        <span className="welcome-queen-role">{queen.role_title}</span>
                      </span>
                      <span className="welcome-queen-crown"><IconCrown size={16} /></span>
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

            {queens.length === 0 && agents.length === 0 && (
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
