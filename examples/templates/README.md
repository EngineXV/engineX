# Templates

| Template | Description |
|----------|-------------|
| [agreement_analysis](agreement_analysis/) | HITL workflow: intake → extract → approval → audit |
| [deep_research](deep_research/) | Multi-source research with HITL review → cited HTML report |
| [log_monitor](log_monitor/) | Always-on Grafana polling → LLM triage → Slack/PagerDuty alerts (`--daemon`) |
| [hourly_tracking](hourly_tracking/) | Hourly reconciliation: validate → fix loop + HITL for exceptions |
| [meeting_scheduler](meeting_scheduler/) | Calendar booking: intake → schedule → confirm (loop) |
| [supervised_agreement_analysis](supervised_agreement_analysis/) | **Supervisor** over the agreement analysis worker |
| [supervisors/](supervisors/) | **Department supervisors** — Technology, Legal, Marketing, and more |
| [support_triage](support_triage/) | Support message triage with human-approved draft replies |
| [invoice_review](invoice_review/) | Invoice extraction with finance approval and audit |

```bash
./engine validate examples/templates/agreement_analysis
./engine run examples/templates/agreement_analysis --tui
```
