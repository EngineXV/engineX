# Hourly Tracking Agent

Hourly reconciliation workflow for broker and investor transactions.

## Workflow

```text
Fetch → Process → Validate ──pass──► Store
                    │
                    ├── auto-fix loop ──► Correct → Validate
                    │
                    └── exception ──► Human Review (HITL) ──approved──► Store
```

## Features

- Hourly execution via `AsyncEntryPointSpec`
- Multi-source transaction ingestion
- Structured transaction normalization
- Deterministic financial validation
- Auto-correction feedback loop
- **Human review** (`pause_nodes=["human_review"]`) when auto-fix cannot resolve discrepancies
- Verified result storage

## Architecture

The agent is implemented as a directed workflow graph with:

- **Entry Node:** `fetch_transactions`
- **Processing Nodes:** Fetch, Process, Validate, Correct, Store
- **Conditional Routing:** Validation determines whether execution proceeds to storage or enters the auto-correction loop.
- **Terminal Node:** `store_results`
- **Scheduler:** `AsyncEntryPointSpec` triggers execution every 60 minutes.

## Validation rule

`input_amount = output_amount + fees`

## Run

```bash
./engine validate examples/templates/hourly_tracking
./engine run examples/templates/hourly_tracking --tui
./engine serve   # approve exceptions in the dashboard
```

For HITL demos without waiting for the timer, use `support_triage` or `agreement_analysis`.
