# Supervised Agreement Analysis

EngineX **supervisor** pattern over the Agreement Analysis worker.

## Architecture

```
Operator ↔ Supervisor (forever-alive lead)
              ↓ spawn_worker / inject_worker_message
           Worker graph (intake → extract → approval → audit)
```

| Layer | Role |
|-------|------|
| **Supervisor** | Your chat interface; delegates tasks and monitors the worker |
| **Worker** | Runs the agreement analysis pipeline (`../agreement_analysis`) |

## Run

```bash
./engine validate examples/templates/supervised_agreement_analysis
./engine run examples/templates/supervised_agreement_analysis --tui
```

Web dashboard: start **Supervised Agreement Analysis** from the home page.

## Example

1. Supervisor greets you in chat.
2. You: “Review this NDA: …” (paste text)
3. Supervisor calls `spawn_worker` — worker runs the pipeline; you approve at HITL gates.
