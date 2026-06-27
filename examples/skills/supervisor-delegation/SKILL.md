---
name: supervisor-delegation
description: Best practices for department supervisors delegating to workers
---

# Supervisor Delegation Skill

Use when operating as a department supervisor with worker spawn tools.

## Workflow

1. Call `list_action_plan()` at session start.
2. When the operator describes work, pick the matching plan `task_id`.
3. Call `spawn_worker(task=..., task_id=...)` once — do not duplicate identical spawns.
4. Use `get_worker_status()` when asked; stay quiet while the worker runs unless input is needed.
5. Mark plan items complete via `update_action_plan_task` when appropriate.

## Rules

- Never fabricate worker output.
- Forward operator messages with `inject_worker_message` when the worker is waiting.
