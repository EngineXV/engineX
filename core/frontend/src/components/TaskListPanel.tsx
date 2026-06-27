export interface TaskRecord {
  id: number;
  subject: string;
  description: string;
  active_form?: string | null;
  owner?: string | null;
  status: "pending" | "in_progress" | "completed";
  blocks: number[];
  blocked_by: number[];
}

interface TaskListPanelProps {
  tasks: TaskRecord[];
  loading?: boolean;
  error?: string | null;
  title?: string;
  onToggle?: (taskId: number, status: TaskRecord["status"]) => void;
}

function statusLabel(status: TaskRecord["status"]) {
  if (status === "in_progress") return "In progress";
  if (status === "completed") return "Done";
  return "Pending";
}

export default function TaskListPanel({ tasks, loading, error, title, onToggle }: TaskListPanelProps) {
  const header = title || "Action plan";
  if (loading) {
    return (
      <aside className="task-panel">
        <div className="task-panel-header">{header}</div>
        <p className="task-panel-empty">Loading…</p>
      </aside>
    );
  }

  if (error) {
    return (
      <aside className="task-panel">
        <div className="task-panel-header">{header}</div>
        <p className="task-panel-error">{error}</p>
      </aside>
    );
  }

  if (tasks.length === 0) {
    return null;
  }

  const done = tasks.filter((t) => t.status === "completed").length;

  return (
    <aside className="task-panel">
      <div className="task-panel-header">
        <span>{header}</span>
        <span className="task-panel-count">
          {done}/{tasks.length}
        </span>
      </div>
      <ul className="task-list">
        {tasks.map((task) => (
          <li key={task.id} className={`task-item task-${task.status}`}>
            <button
              type="button"
              className="task-check"
              aria-label={`Mark task ${task.id} complete`}
              onClick={() =>
                onToggle?.(
                  task.id,
                  task.status === "completed" ? "pending" : "completed",
                )
              }
            >
              {task.status === "completed" ? "✓" : ""}
            </button>
            <div className="task-body">
              <div className="task-subject">{task.active_form || task.subject}</div>
              {task.description ? (
                <div className="task-description">{task.description}</div>
              ) : null}
              <div className="task-meta">{statusLabel(task.status)}</div>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
