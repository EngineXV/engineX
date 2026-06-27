---
name: agreement-review
description: Human-in-the-loop checklist for agreement extraction workflows
---

# Agreement Review Skill

Use when reviewing extracted contract fields before approval.

## Checklist

1. Confirm parties match the source document verbatim.
2. Verify dates and term length — flag "Not found" fields explicitly.
3. Compare liability cap against operator policy thresholds.
4. Ask the reviewer to approve or edit before audit finalization.

## Output

When the reviewer approves, record `review_decision=approved` and copy final values to `approved_*` fields.
