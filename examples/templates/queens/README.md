# Queen Bees

Hive-style **department Queen Bees** — each Queen supervises the Agreement Analysis worker with a domain-specific persona.

| Queen | Department | Role |
|-------|------------|------|
| Alexandra | Technology | Head of Technology |
| Rachel | Operations | Head of Operations |
| Eleanor | Legal | Head of Legal |
| Catherine | Marketing | Head of Marketing |
| Victoria | Growth | Head of Growth |
| Charlotte | Finance | Head of Finance |
| Sophia | Brand & Design | Head of Brand & Design |

## Run

```bash
./engine validate examples/templates/queens/legal
./engine run examples/templates/queens/legal --tui
```

Web dashboard: open any Queen from the **Queen Bees** section in the sidebar.

## Architecture

Each queen is a thin config over `queen_factory.py` — same supervisor tools, department-tuned system prompt, shared worker (`../agreement_analysis`).
