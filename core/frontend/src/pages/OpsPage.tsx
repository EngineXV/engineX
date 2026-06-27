import { useEffect, useState } from "react";
import DashboardHeader from "../components/DashboardHeader";
import { useDashboard } from "../context/DashboardContext";
import { api, type OpsAlert, type OpsRun } from "../api";

export default function OpsPage() {
  const { model } = useDashboard();
  const [runs, setRuns] = useState<OpsRun[]>([]);
  const [alerts, setAlerts] = useState<OpsAlert[]>([]);
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getOpsRuns(), api.getOpsAlerts(), api.getOpsSummary()])
      .then(([runRes, alertRes, summary]) => {
        setRuns(runRes.runs);
        setAlerts(alertRes.alerts);
        setMetrics(summary.metrics as Record<string, unknown>);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div className="ops-page">
      <DashboardHeader session={null} model={model} connected />
      {error ? <div className="error-banner">{error}</div> : null}

      <div className="ops-grid">
        <section className="ops-card">
          <h2>Metrics</h2>
          {metrics ? (
            <dl className="ops-metrics">
              {Object.entries((metrics.counters as Record<string, number>) || {}).map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
              {Object.entries((metrics.gauges as Record<string, number>) || {}).map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p>Loading metrics…</p>
          )}
          <a className="ops-link" href="/api/ops/metrics" target="_blank" rel="noreferrer">
            Prometheus export
          </a>
        </section>

        <section className="ops-card">
          <h2>Alerts</h2>
          <ul className="ops-alert-list">
            {alerts.map((alert, index) => (
              <li key={`${alert.title}-${index}`} className={`ops-alert ops-alert-${alert.severity}`}>
                <strong>{alert.title}</strong>
                <p>{alert.message}</p>
                {alert.timestamp ? <time>{alert.timestamp}</time> : null}
              </li>
            ))}
          </ul>
        </section>

        <section className="ops-card ops-card-wide">
          <h2>Run history</h2>
          <div className="ops-table-wrap">
            <table className="ops-table">
              <thead>
                <tr>
                  <th>Agent</th>
                  <th>Execution</th>
                  <th>Status</th>
                  <th>Checkpoints</th>
                  <th>Started</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.execution_id}>
                    <td>{run.agent}</td>
                    <td><code>{run.execution_id.slice(0, 14)}…</code></td>
                    <td><span className={`status-chip status-${run.status}`}>{run.status}</span></td>
                    <td>{run.checkpoint_count}</td>
                    <td>{run.started_at || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
