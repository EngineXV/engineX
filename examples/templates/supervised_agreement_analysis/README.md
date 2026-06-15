# Supervised Agreement Analysis

Hive-style **Queen Bee** supervision over the Agreement Analysis worker.

## Architecture

```
Operator ↔ Queen (forever-alive supervisor)
              ↓ start_worker / inject_worker_message
           Worker graph (intake → extract → approval → audit)
```

| Layer | Role |
|-------|------|
| **Queen** | Your chat interface; delegates tasks and monitors the worker |
| **Worker** | Runs the agreement analysis pipeline (`../agreement_analysis`) |

## Run

```bash
./engine validate examples/templates/supervised_agreement_analysis
./engine run examples/templates/supervised_agreement_analysis --tui
```

Web dashboard: start **Supervised Agreement Analysis** from the home page.

## Example

1. Queen greets you in chat.
2. You: “Review this NDA: …” (paste text)
3. Queen calls `start_worker` → worker intake runs.
4. Worker pauses at approval gate → you reply in chat (routed to worker when waiting).
