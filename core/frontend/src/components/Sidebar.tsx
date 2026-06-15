import { useCallback, useState, type ReactNode } from "react";
import { NavLink, useLocation, useMatch, useNavigate } from "react-router-dom";
import { useDashboard } from "../context/DashboardContext";
import {
  IconAgent,
  IconBook,
  IconChevronLeft,
  IconChevronRight,
  IconEngine,
  IconKey,
  IconOrgChart,
  IconPlus,
  IconSupervisor,
} from "./Icons";

type SectionKey = "supervisors" | "workflows" | "sessions";

function CollapsibleSection({
  sectionKey,
  title,
  hint,
  count,
  open,
  onToggle,
  children,
}: {
  sectionKey: SectionKey;
  title: string;
  hint: string;
  count: number;
  open: boolean;
  onToggle: (key: SectionKey) => void;
  children: ReactNode;
}) {
  return (
    <section className={`sidebar-section sidebar-section--${sectionKey}${open ? "" : " is-collapsed"}`}>
      <button
        type="button"
        className="sidebar-section-toggle"
        onClick={() => onToggle(sectionKey)}
        aria-expanded={open}
      >
        <span className="sidebar-section-toggle-text">
          <span className="sidebar-section-label">{title}</span>
          <span className="sidebar-section-hint">{hint}</span>
        </span>
        <span className="sidebar-section-count">{count}</span>
        <IconChevronRight size={14} className={`sidebar-section-chevron${open ? " is-open" : ""}`} />
      </button>
      {open && <div className="sidebar-section-body">{children}</div>}
    </section>
  );
}

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const sessionMatch = useMatch("/session/:sessionId");
  const { supervisors, agents, sessions, loading, openAgent } = useDashboard();
  const [collapsed, setCollapsed] = useState(false);
  const [starting, setStarting] = useState<string | null>(null);
  const [sectionsOpen, setSectionsOpen] = useState<Record<SectionKey, boolean>>({
    supervisors: true,
    workflows: true,
    sessions: true,
  });

  const toggleSection = useCallback((key: SectionKey) => {
    setSectionsOpen((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const activeSession = sessionMatch
    ? sessions.find((s) => s.session_id === sessionMatch.params.sessionId)
    : undefined;
  const activeAgentPath = activeSession?.agent_path;
  const isHome = location.pathname === "/";

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
        <NavLink to="/" end className={({ isActive }) => `nav-item nav-home${isActive && isHome ? " active" : ""}`}>
          <span className="nav-icon"><IconPlus size={16} /></span>
          New Session
        </NavLink>
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

      <div className="sidebar-scroll">
        <CollapsibleSection
          sectionKey="supervisors"
          title="Supervisors"
          hint="Department leads"
          count={supervisors.length}
          open={sectionsOpen.supervisors}
          onToggle={toggleSection}
        >
          {loading && <div className="sidebar-empty">Loading…</div>}
          {!loading && supervisors.length === 0 && (
            <div className="sidebar-empty">No supervisors found</div>
          )}
          {supervisors.map((supervisor) => (
            <button
              key={supervisor.path}
              type="button"
              className={`sidebar-supervisor${activeAgentPath === supervisor.path ? " active" : ""}`}
              disabled={starting === supervisor.path}
              onClick={() => void handleOpenAgent(supervisor.path)}
            >
              <span className="supervisor-avatar">
                <span className="status-dot on" />
                {(supervisor.supervisor_name || supervisor.name).charAt(0).toUpperCase()}
              </span>
              <span className="agent-meta">
                <span className="agent-name">{supervisor.supervisor_name || supervisor.name}</span>
                <span className="agent-sub">{supervisor.department}</span>
              </span>
              <IconSupervisor size={14} className="sidebar-row-mark" />
            </button>
          ))}
        </CollapsibleSection>

        {agents.length > 0 && (
          <>
            <div className="sidebar-section-divider" role="separator" aria-hidden />
            <CollapsibleSection
              sectionKey="workflows"
              title="Workflow agents"
              hint="Automated pipelines"
              count={agents.length}
              open={sectionsOpen.workflows}
              onToggle={toggleSection}
            >
              {agents.map((agent) => (
                <button
                  key={agent.path}
                  type="button"
                  className={`sidebar-agent${activeAgentPath === agent.path ? " active" : ""}`}
                  disabled={starting === agent.path}
                  onClick={() => void handleOpenAgent(agent.path)}
                >
                  <span className="agent-avatar">{agent.name.charAt(0).toUpperCase()}</span>
                  <span className="agent-meta">
                    <span className="agent-name">{agent.name}</span>
                    <span className="agent-sub">{agent.node_count} nodes</span>
                  </span>
                  {agent.is_loaded ? (
                    <span className="status-pill">live</span>
                  ) : (
                    <IconAgent size={14} className="sidebar-row-mark" />
                  )}
                </button>
              ))}
            </CollapsibleSection>
          </>
        )}

        {sessions.length > 0 && (
          <>
            <div className="sidebar-section-divider" role="separator" aria-hidden />
            <CollapsibleSection
              sectionKey="sessions"
              title="Sessions"
              hint="Active runs"
              count={sessions.length}
              open={sectionsOpen.sessions}
              onToggle={toggleSection}
            >
              {sessions.map((session) => (
                <NavLink
                  key={session.session_id}
                  to={`/session/${session.session_id}`}
                  className={({ isActive }) => `sidebar-session${isActive ? " active" : ""}`}
                >
                  <span className={`status-dot ${session.current_exec_id ? "on" : "off"}`} />
                  <span className="session-label">
                    {session.supervisor_name || session.name}
                    {session.department ? ` · ${session.department}` : ""}
                  </span>
                </NavLink>
              ))}
            </CollapsibleSection>
          </>
        )}
      </div>
    </aside>
  );
}
