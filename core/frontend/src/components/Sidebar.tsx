import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useDashboard } from "../context/DashboardContext";
import {
  IconBook,
  IconChevronLeft,
  IconChevronRight,
  IconCrown,
  IconEngine,
  IconKey,
  IconOrgChart,
  IconPlus,
} from "./Icons";

export default function Sidebar() {
  const navigate = useNavigate();
  const { queens, agents, sessions, loading, openAgent } = useDashboard();
  const [collapsed, setCollapsed] = useState(false);
  const [starting, setStarting] = useState<string | null>(null);

  const handleOpenAgent = async (path: string) => {
    setStarting(path);
    try {
      const session = await openAgent(path);
      navigate(`/session/${session.session_id}`);
    } catch (e) {
      console.error(e);
    } finally {
      setStarting(null);
    }
  };

  if (collapsed) {
    return (
      <aside className="sidebar sidebar-collapsed">
        <button type="button" className="sidebar-toggle" onClick={() => setCollapsed(false)} title="Expand sidebar">
          <IconChevronRight size={16} />
        </button>
      </aside>
    );
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <button type="button" className="brand-mark" onClick={() => navigate("/")} title="Home">
          <IconEngine size={22} />
        </button>
        <button type="button" className="brand-text brand-link" onClick={() => navigate("/")}>
          Engine
        </button>
        <button type="button" className="sidebar-toggle" onClick={() => setCollapsed(true)} title="Collapse sidebar">
          <IconChevronLeft size={16} />
        </button>
      </div>

      <nav className="sidebar-nav">
        <button type="button" className="nav-item nav-primary" onClick={() => navigate("/")}>
          <span className="nav-icon"><IconPlus size={16} /></span>
          New Session
        </button>
        <NavLink to="/org-chart" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          <span className="nav-icon"><IconOrgChart size={16} /></span>
          Org Chart
        </NavLink>
        <NavLink to="/credentials" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          <span className="nav-icon"><IconKey size={16} /></span>
          Credentials
        </NavLink>
        <NavLink to="/skills" className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}>
          <span className="nav-icon"><IconBook size={16} /></span>
          Skills
        </NavLink>
      </nav>

      <div className="sidebar-section">
        <div className="sidebar-section-label">Queen Bees</div>
        {loading && <div className="sidebar-empty">Loading…</div>}
        {!loading && queens.length === 0 && (
          <div className="sidebar-empty">No queens found</div>
        )}
        {queens.map((queen) => (
          <button
            key={queen.path}
            type="button"
            className="sidebar-queen"
            disabled={starting === queen.path}
            onClick={() => void handleOpenAgent(queen.path)}
          >
            <span className="queen-avatar">
              <span className="status-dot on" />
              {(queen.queen_name || queen.name).charAt(0).toUpperCase()}
            </span>
            <span className="agent-meta">
              <span className="agent-name">{queen.queen_name || queen.name}</span>
              <span className="agent-sub">{queen.department}</span>
            </span>
            <IconCrown size={14} className="queen-crown-icon" />
          </button>
        ))}
      </div>

      {agents.length > 0 && (
        <div className="sidebar-section">
          <div className="sidebar-section-label">Agents</div>
          {agents.map((agent) => (
            <button
              key={agent.path}
              type="button"
              className="sidebar-agent"
              disabled={starting === agent.path}
              onClick={() => void handleOpenAgent(agent.path)}
            >
              <span className="agent-avatar">{agent.name.charAt(0).toUpperCase()}</span>
              <span className="agent-meta">
                <span className="agent-name">{agent.name}</span>
                <span className="agent-sub">{agent.node_count} nodes</span>
              </span>
              {agent.is_loaded && <span className="status-pill">live</span>}
            </button>
          ))}
        </div>
      )}

      {sessions.length > 0 && (
        <div className="sidebar-section">
          <div className="sidebar-section-label">Sessions</div>
          {sessions.map((session) => (
            <NavLink
              key={session.session_id}
              to={`/session/${session.session_id}`}
              className={({ isActive }) => `sidebar-session${isActive ? " active" : ""}`}
            >
              <span className={`status-dot ${session.current_exec_id ? "on" : "off"}`} />
              <span className="session-label">
                {session.queen_name || session.name}
                {session.department ? ` · ${session.department}` : ""}
              </span>
            </NavLink>
          ))}
        </div>
      )}
    </aside>
  );
}
