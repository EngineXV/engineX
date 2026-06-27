# Templates

| Template | Description |
|----------|-------------|
| [agreement_analysis](agreement_analysis/) | HITL workflow: intake → extract → approval → audit |
| [meeting_scheduler](meeting_scheduler/) | Calendar booking: intake → schedule → confirm (loop) |
| [supervised_agreement_analysis](supervised_agreement_analysis/) | **Supervisor** over the agreement analysis worker |
| [supervisors/](supervisors/) | **Department supervisors** — Technology, Legal, Marketing, and more |

```bash
./engine validate examples/templates/agreement_analysis
./engine run examples/templates/agreement_analysis --tui
```
