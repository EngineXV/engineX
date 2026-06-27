import { useCallback, useEffect, useState } from "react";
import { api, type CheckpointSummary, type ExecutionSummary } from "../api";

interface CheckpointPanelProps {
  sessionId: string;
}

export default function CheckpointPanel({ sessionId }: CheckpointPanelProps) {
  const [executions, setExecutions] = useState<ExecutionSummary[]>([]);
  const [selectedExecution, setSelectedExecution] = useState<string>("");
  const [checkpoints, setCheckpoints] = useState<CheckpointSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadExecutions = useCallback(async () => {
    const res = await api.listExecutions(sessionId);
    setExecutions(res.executions);
    if (res.executions.length > 0) {
      setSelectedExecution((current) => current || res.executions[0]!.execution_id);
    }
  }, [sessionId]);

  const loadCheckpoints = useCallback(async () => {
    if (!selectedExecution) {
      setCheckpoints([]);
      return;
    }
    const res = await api.listCheckpoints(sessionId, selectedExecution);
    setCheckpoints(res.checkpoints);
  }, [sessionId, selectedExecution]);

  useEffect(() => {
    void loadExecutions().catch(() => setExecutions([]));
  }, [loadExecutions]);

  useEffect(() => {
    void loadCheckpoints().catch(() => setCheckpoints([]));
  }, [loadCheckpoints]);

  const resumeFrom = async (checkpointId: string) => {
    if (!selectedExecution) return;
    setBusy(true);
    setMessage(null);
    try {
      const res = await api.resumeFromCheckpoint(sessionId, selectedExecution, checkpointId);
      setMessage(`Resumed from ${checkpointId.slice(0, 24)}… (exec ${res.execution_id.slice(0, 12)})`);
      await loadExecutions();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Resume failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="checkpoint-panel" aria-label="Checkpoint recovery">
      <div className="checkpoint-panel-header">
        <strong>Checkpoints</strong>
        <button type="button" className="btn-secondary btn-small" onClick={() => void loadExecutions()}>
          Refresh
        </button>
      </div>

      {executions.length === 0 ? (
        <p className="checkpoint-empty">No executions with checkpoints yet.</p>
      ) : (
        <>
          <label className="checkpoint-select-label">
            Execution
            <select
              value={selectedExecution}
              onChange={(e) => setSelectedExecution(e.target.value)}
            >
              {executions.map((item) => (
                <option key={item.execution_id} value={item.execution_id}>
                  {item.execution_id.slice(0, 16)}… ({item.checkpoint_count})
                </option>
              ))}
            </select>
          </label>

          <ul className="checkpoint-list">
            {checkpoints.map((cp) => (
              <li key={cp.checkpoint_id} className="checkpoint-item">
                <div>
                  <strong>{cp.description || cp.checkpoint_type}</strong>
                  <span>{cp.current_node}</span>
                  <time>{cp.created_at}</time>
                </div>
                <button
                  type="button"
                  className="btn-secondary btn-small"
                  disabled={busy}
                  onClick={() => void resumeFrom(cp.checkpoint_id)}
                >
                  Resume
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      {message ? <p className="checkpoint-message">{message}</p> : null}
    </section>
  );
}
