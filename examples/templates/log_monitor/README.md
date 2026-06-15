# Log Monitor Agent

Grafana log monitoring: filtered fetch → dedup → score → LLM triage → Slack/PagerDuty/Jira → human review → learn.

## Flow

```
Timer (1 min) → Fetch & Enrich → [LLM Triage] → Dispatch → [Human Review] → Learn
```

## Quick start (dev / mock)

```bash
./engine validate examples/templates/log_monitor
./engine run examples/templates/log_monitor --input '{}' --allow-mock
```

Uses sample logs when Grafana is not configured.

## Production deployment

### 1. Configure credentials

Copy `examples/templates/log_monitor/.env.example` → `/etc/engine/log-monitor.env` and fill in:

- `GRAFANA_URL`, `GRAFANA_API_TOKEN`, `GRAFANA_DATASOURCE_UID`
- `SLACK_WEBHOOK_URL`
- `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`)
- Optional: `PAGERDUTY_ROUTING_KEY`, Jira vars

Optional local files under `~/.engine/log_monitor/`:

- `service_catalog.json` — `{"payments-api": {"owner": "@payments-oncall"}}`
- `deploy_events.json` — recent deploy events for correlation

### 2. Validate config

```bash
set -a && source /etc/engine/log-monitor.env && set +a
./engine run examples/templates/log_monitor --daemon --require-live --allow-mock
# Ctrl+C after "Daemon running" confirms startup
```

Remove `--allow-mock` in production.

### 3. Run as daemon (headless)

```bash
./engine run examples/templates/log_monitor --daemon --require-live
```

Timer polls every **1 minute**. MEDIUM severity:

- **TUI mode** (`--tui`): human approval gate
- **Daemon mode** (`--daemon`): auto-posts MEDIUM digest to Slack (no blocking HITL)

### 4. systemd (optional)

See `deploy/engine-log-monitor.service`. Install:

```bash
sudo cp deploy/engine-log-monitor.service /etc/systemd/system/
sudo systemctl enable --now engine-log-monitor
```

## Commands

| Command | Use |
|---------|-----|
| `./engine validate examples/templates/log_monitor` | Check graph |
| `./engine run ... --input '{}'` | Single manual tick |
| `./engine run ... --tui` | Interactive dashboard + timer |
| `./engine run ... --daemon --require-live` | Production headless |
| `./engine run ... --allow-mock` | Dev without Grafana |

## Environment reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOG_MONITOR_KEYWORDS` | error,exception,fatal,panic | LogQL filter |
| `LOG_MONITOR_LOOKBACK_MINUTES` | 1 | Query window |
| `LOG_MONITOR_MUTE_MINUTES` | 30 | Skip re-processing same fingerprint |
| `LOG_MONITOR_ALERT_COOLDOWN_MINUTES` | 15 | Skip repeat Slack/PagerDuty alerts |
| `LOG_MONITOR_DAEMON` | — | Set by `--daemon` |
| `LOG_MONITOR_ALLOW_MOCK` | — | Set by `--allow-mock` |

## Architecture

External inputs: Grafana, metrics/deploy context, service catalog.

Engine core: dedup, rule scoring, LLM triage (ambiguous only), routing.

External outputs: Slack, PagerDuty (SEVERE), Jira, human review (TUI), learn store.
