# Log Monitor Agent

Polls Grafana every 1 min for filtered errors → dedup → score → LLM triage → alert → learn.

```
Timer → Fetch & Enrich → [LLM Triage] → Dispatch → [Human Review] → Learn
```

---

## Steps — local dev (mock logs)

1. **Validate the agent**
   ```bash
   ./engine validate examples/templates/log_monitor
   ```

2. **Run one tick** (no Grafana needed)
   ```bash
   ./engine run examples/templates/log_monitor --input '{}' --allow-mock
   ```

3. **Run with TUI** (timer + human review for MEDIUM)
   ```bash
   ./engine run examples/templates/log_monitor --tui --allow-mock
   ```

---

## Steps — production

1. **Copy and fill credentials**
   ```bash
   cp examples/templates/log_monitor/.env.example /etc/engine/log-monitor.env
   ```
   Required: `GRAFANA_URL`, `GRAFANA_API_TOKEN`, `GRAFANA_DATASOURCE_UID`, `SLACK_WEBHOOK_URL`, `ANTHROPIC_API_KEY`  
   Optional: `PAGERDUTY_ROUTING_KEY`, Jira vars (`JIRA_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`)

2. **Load env and validate**
   ```bash
   set -a && source /etc/engine/log-monitor.env && set +a
   ./engine validate examples/templates/log_monitor
   ```

3. **Start headless daemon**
   ```bash
   ./engine run examples/templates/log_monitor --daemon --require-live
   ```
   - SEVERE/HIGH → Slack + PagerDuty (SEVERE) + Jira  
   - MEDIUM → Slack digest (no human gate in daemon mode)  
   - Duplicates muted for 30 min; repeat alerts cooled down for 15 min

4. **Optional — run as a service**
   ```bash
   sudo cp examples/templates/log_monitor/deploy/engine-log-monitor.service /etc/systemd/system/
   sudo systemctl enable --now engine-log-monitor
   ```

---

## Optional setup

| File | Purpose |
|------|---------|
| `~/.engine/log_monitor/service_catalog.json` | Map service → owner (`@team`) |
| `~/.engine/log_monitor/deploy_events.json` | Recent deploys for correlation |

---

## Commands cheat sheet

| Command | When |
|---------|------|
| `--input '{}'` | Single manual run |
| `--tui` | Interactive dashboard + human approval |
| `--daemon --require-live` | Production headless |
| `--allow-mock` | Dev without Grafana |

---

## Key env vars

| Variable | Default |
|----------|---------|
| `LOG_MONITOR_KEYWORDS` | `error,exception,fatal,panic` |
| `LOG_MONITOR_LOOKBACK_MINUTES` | `1` |
| `LOG_MONITOR_MUTE_MINUTES` | `30` |
| `LOG_MONITOR_ALERT_COOLDOWN_MINUTES` | `15` |
