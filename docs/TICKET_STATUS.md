# EngineX Ticket Audit — Post PR #9 / #11 / #12

**Audit date:** 2026-06-14 (updated)  
**Code baseline:** `main` + local changes (deep_research, hourly_tracking HITL, GOALS.md, MULTI_TENANT.md)  
**Repos:** [EngineXV/engineX](https://github.com/EngineXV/engineX) (public) · [EngineXV/engineX-internal](https://github.com/EngineXV/engineX-internal) (private GTM)

This document tracks whether open tickets and diagrams match the product after OSS platform polish.

---

## Summary

| Area | Status |
|------|--------|
| **Engineering merged** | PR #9 (hourly tracking), #11 (supervisors), #12 (OAuth, ops, checkpoints, GCU) |
| **Docs updated locally** | `ENGINEX_COMPLETE_GUIDE.md`, `CLIENT_DEPLOYMENT_GUIDE.md`, `GOALS.md`, `MULTI_TENANT.md`, `TICKET_STATUS.md`, templates README |
| **Still open (engineering)** | #10 (GOALS.md done — close after commit) · #4 multi-tenant (design doc only — implementation Phase 2) · #5 desktop |
| **Still open (GTM internal)** | All 8 internal tickets — business deliverables, not code |

---

## Public repo — EngineXV/engineX

### Closed / done — verify ticket body vs reality

| # | Title | Code status | Ticket / diagram notes |
|---|-------|-------------|------------------------|
| **#2** | Hourly Tracking Agent | **Done** — `examples/templates/hourly_tracking/`, PR #9 merged; v1.1 adds `pause_nodes` HITL for unresolved exceptions | Architecture diagram still accurate. |
| **#1** | LLM Auto-Correction | **Done in runtime** — judge RETRY in `event_loop/node.py`, not separate `EvaluationNode` | Closed correctly. Diagram showing standalone EvaluationNode is **outdated** — judge runs inside EventLoopNode. |
| **#3, #6, #7** | Phase 3 agents | **wontfix** | Diagrams reference `hitl.py` + "Resolution Handshake Node" — partially valid (`graph/hitl.py` exists) but overspecifies unbuilt agent scaffolding. OK as backlog/wontfix. |

### Open — up to date?

| # | Title | Up to date? | Action needed |
|---|-------|-------------|---------------|
| **#4** | Multi-Tenant Architecture | **Yes** — accurately describes single-tenant OSS today | **`docs/MULTI_TENANT.md`** added (design spec). No OSS implementation — Phase 2 / Engine Cloud. |
| **#5** | Desktop Agents | **Mostly yes** — run-mode table accurate | **Minor update:** add Ops console + checkpoint API on server (PR #12) as built server-side capabilities. Desktop connector still not built. |
| **#10** | Goal vs node criteria docs | **Mostly done** | **`docs/GOALS.md`** + README link shipped. Tests and Level 2 examples already in tree. Close #10 after commit. |

### PRs (reference)

| PR | Status | Maps to |
|----|--------|---------|
| #9 | Merged | Issue #2 |
| #11 | Merged | Supervisor platform (not a standalone issue) |
| #12 | Merged | OSS polish — closes gaps listed in old #10 "improvement gaps" for HITL UI, ops, OAuth |

---

## Private repo — EngineXV/engineX-internal

| # | Title | Up to date? | Notes after engineering work |
|---|-------|-------------|------------------------------|
| **#1** | Demo video | **Needs re-record** | Platform now has Ops page, checkpoint picker, HITL evidence, OAuth Connect, 7+7 agents in discover. Script should reference PR #12 features. |
| **#2** | Design partner | **Unchanged** | Business/sales — not blocked by code |
| **#3** | Investor deck | **Needs refresh** | Include supervisor platform, ops console, client self-host model (`CLIENT_DEPLOYMENT_GUIDE.md`) |
| **#4** | Pilot pricing | **Unchanged** | Business |
| **#5** | Client onboarding runbook | **Partially addressed** | **`docs/CLIENT_DEPLOYMENT_GUIDE.md`** covers install, headless vs UI, inputs, diagrams. Still need: kickoff template, hypercare checklist, pricing tie-in |
| **#6** | Security brief | **Partially addressed** | Deployment guide §9 + ENGINEX §22 cover VPC, no DB, encrypted vault, no tenancy. Still need: 1-page PDF for finance reviewers |
| **#7** | Integrations narrative | **Partially addressed** | `examples/templates/integrations/README.md` + OAuth in dashboard. Still need: 2-page sales doc |
| **#8** | Landing page | **Unchanged** | README has doc links now; no public landing page |

---

## Diagram review

### Accurate (no change required)

| Location | Diagram | Verdict |
|----------|---------|---------|
| engineX **#4** | Auth + tenant middleware sequence | Correct target architecture; OSS not there yet |
| engineX **#4** | Tenant A / B isolation | Correct |
| engineX **#5** | Cloud ↔ desktop sequence | Correct for future desktop connector |
| engineX **#10** | Goal vs node layer | Correct |
| engineX **#10** | Four feedback mechanisms | Correct |
| engineX **#2** | Hourly tracking pipeline | Correct |
| `CLIENT_DEPLOYMENT_GUIDE.md` | Client VPC architecture | Correct — matches filesystem storage, no Engine Cloud required |
| `CLIENT_DEPLOYMENT_GUIDE.md` | Headless vs hybrid | Correct |
| `ENGINEX_COMPLETE_GUIDE.md` | Master anatomy / behavioral maps | Correct after Queen→Supervisor rename |

### Stale — fixed or flagged

| Location | Issue | Fix |
|----------|-------|-----|
| `ENGINEX_COMPLETE_GUIDE.md` | `QueenSupervisor`, `queen_supervisor.py` | **Fixed** → `supervisor_runtime.py` |
| `ENGINEX_COMPLETE_GUIDE.md` §22 | "HITL evidence UI not built" | **Fixed** — PR #12 shipped |
| `ENGINEX_COMPLETE_GUIDE.md` §15 | Missing Ops, Checkpoints, OAuth, HITL panel | **Fixed** |
| engineX **#1** (closed) | Standalone EvaluationNode | Historical — document judge-in-event-loop instead |
| Phase 3 agent tickets | "Resolution Handshake Node" as product feature | Aspirational — real path is `pause_nodes` + `inject_input` + `HitlReviewPanel` |
| `HIVE_COMPLETE_GUIDE.md` | Duplicate of ENGINEX with old names | **Do not use** — prefer `ENGINEX_COMPLETE_GUIDE.md` |

### Diagram improvement suggestions (optional)

1. **#5 Desktop ticket** — add note on diagram: "Primary path today = client installs OSS in their VPC" (link deployment guide).
2. **Internal #5** — link `CLIENT_DEPLOYMENT_GUIDE.md` decision tree in onboarding steps.
3. **#10** — when `GOALS.md` is written, use the four-mechanism diagram from the issue (already good).

---

## Recommended next ticket actions

### Engineering (public)

1. **#10** — Close after `docs/GOALS.md` lands on `main`.
2. **#4** — Design doc at `docs/MULTI_TENANT.md`; implementation remains Phase 2.
3. **#5** — Comment: server-side ops/checkpoints/OAuth shipped; desktop connector still Phase 3.

### GTM (internal)

1. **#5** — Link `docs/CLIENT_DEPLOYMENT_GUIDE.md` as engineering appendix.
2. **#1** — Re-record demo including Ops + checkpoint resume + credentials OAuth.
3. **#6 / #7** — Pull security + integrations bullets from deployment guide into 1–2 page PDFs.

---

## Local doc files (not yet on main unless committed)

| File | Purpose |
|------|---------|
| `docs/CLIENT_DEPLOYMENT_GUIDE.md` | Client install ticket / handoff |
| `docs/GOALS.md` | Goal vs node criteria (#10) |
| `docs/MULTI_TENANT.md` | Multi-tenant design spec (#4) |
| `docs/TICKET_STATUS.md` | This audit |
| `docs/ENGINEX_COMPLETE_GUIDE.md` | Updated gaps + naming |
| `examples/templates/deep_research/` | Deep research template |
