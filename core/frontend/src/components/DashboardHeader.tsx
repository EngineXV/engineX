import type { SessionDetail } from "../api";
import { IconCrown } from "./Icons";

interface DashboardHeaderProps {
  session: SessionDetail | null;
  model: string;
  connected: boolean;
}

export default function DashboardHeader({ session, model, connected }: DashboardHeaderProps) {
  const isQueen = session?.queen_bee || session?.supervised;
  const title = session?.queen_name || session?.name || "Engine Dashboard";
  const subtitle = session?.role_title || session?.description || session?.goal || "Pick a Queen or agent to start";

  return (
    <header className="dash-header">
      <div className="dash-header-left">
        <div className="dash-title-row">
          {isQueen && (
            <span className="dash-crown" aria-hidden>
              <IconCrown size={20} />
            </span>
          )}
          <h1>{title}</h1>
          {session?.role_title && (
            <span className="role-badge role-badge-queen">{session.role_title}</span>
          )}
          {session && !session.role_title && (
            <span className="role-badge">
              {session.supervised ? "Queen" : "Agent"}
            </span>
          )}
        </div>
        <p className="dash-subtitle">{subtitle}</p>
      </div>
      <div className="dash-header-right">
        <span className={`live-badge ${connected ? "on" : "off"}`}>
          <span className="status-dot" />
          {connected ? "Connected" : "Offline"}
        </span>
        <span className="model-badge" title={model}>{model}</span>
      </div>
    </header>
  );
}
