# Department Supervisors

Each **supervisor** is a department lead that oversees the Agreement Analysis worker with a domain-specific persona.

| Lead | Department | Role |
|------|------------|------|
| Alexandra | Technology | Head of Technology |
| Rachel | Operations | Head of Operations |
| Eleanor | Legal | Head of Legal |
| Catherine | Marketing | Head of Marketing |
| Victoria | Growth | Head of Growth |
| Charlotte | Finance | Head of Finance |
| Sophia | Brand & Design | Head of Brand & Design |

## Run

```bash
./engine validate examples/templates/supervisors/legal
./engine run examples/templates/supervisors/legal --tui
```

Web dashboard: open any supervisor from the **Supervisors** section in the sidebar.

## Architecture

Each supervisor is a thin config over `supervisor_factory.py` — same lifecycle tools, department-tuned system prompt, shared worker (`../agreement_analysis`).

## Supervisor plan + worker spawn

When you start a supervisor from the dashboard:

1. A **Supervisor plan** is seeded (department defaults) and shown in the session sidebar.
2. The supervisor can refine it with `create_action_plan`, `list_action_plan`, and `update_action_plan_task`.
3. **`spawn_worker(task)`** starts the agreement-analysis worker for a plan item; status moves to *in progress* and back to *completed* when the worker finishes.

One worker runs at a time per supervisor session.
