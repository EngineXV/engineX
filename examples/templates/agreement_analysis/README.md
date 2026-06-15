# Agreement Analysis

Structured extraction of agreement terms with **human-in-the-loop** approval and audit trail.

## Flow

```
intake → extract → human_review → audit
```

| Node | Type | Purpose |
|------|------|---------|
| intake | client-facing | Collect agreement text |
| extract | LLM | Extract parties, dates, terms, liability |
| human_review | client-facing | Reviewer approves or edits |
| audit | LLM | Produce audit record + summary |

## Run

```bash
./engine validate examples/templates/agreement_analysis
./engine run examples/templates/agreement_analysis --tui
```

Headless (requires full HITL support in your integration):

```bash
./engine run examples/templates/agreement_analysis \
  --input '{"contract_text": "...", "document_name": "NDA-2026"}'
```

## Build your product on top

Wrap this agent in your SaaS API: upload PDF → call engine → show review UI on `human_review` pause → store `audit_record`.
