# DecisionLog

**Turn messy meeting notes into a living decision log.**

Most meeting tools capture *what was said*.  
DecisionLog captures **what was decided**, **who owns it**, and **when it is due** — then keeps it searchable and updatable.

**Current version: 0.2.1** — solid local-first CLI. Further product work paused until the next focused iteration.

---

## The Real Pain

After almost every meeting:

- Decisions get buried in long transcripts or Notion pages
- Action items are written down but ownership is fuzzy (“someone should…”) 
- Deadlines are vague (“next week”) or missing
- Three weeks later nobody remembers *why* a decision was made or who is accountable

**DecisionLog focuses on the overlooked middle layer**: reliable extraction of *decisions* + *owned actions* into a clean, queryable, updatable log.

---

## What it does

1. Takes a meeting transcript or notes
2. Uses an LLM to extract clear **decisions** and **action items** (with owners, deadlines, evidence, confidence)
3. **Normalizes relative deadlines** (`next Friday`, `end of month`, `in 2 weeks`, …) into concrete dates
4. Stores everything in a local SQLite decision log
5. Supports **re-run / replace** on the same meeting title
6. **Status updates**, **show details**, **list filters**, **Markdown + JSON export**

---

## Quick Start

```bash
git clone https://github.com/VSBhargav5/DecisionLog.git
cd DecisionLog
pip install -r requirements.txt

export OPENAI_API_KEY="sk-..."   # or any OpenAI-compatible endpoint
```

### Extract

```bash
python -m decisionlog extract examples/sample_meeting.txt \
  -m "Sprint Planning 31 Jul" \
  --date 2026-07-31
```

Re-run the same meeting (overwrite previous extraction):

```bash
python -m decisionlog extract examples/sample_meeting.txt \
  -m "Sprint Planning 31 Jul" \
  --date 2026-07-31 \
  --replace
```

### List / filter

```bash
python -m decisionlog list actions
python -m decisionlog list actions --status open --owner Sarah
python -m decisionlog list actions --meeting "Sprint Planning 31 Jul"
python -m decisionlog list decisions
python -m decisionlog list meetings
```

### Show one item

```bash
python -m decisionlog show <id>                 # action (default)
python -m decisionlog show <id> --kind decision
```

### Update status

```bash
python -m decisionlog status <id> done
python -m decisionlog status <id> in_progress --owner Sarah
python -m decisionlog status <id> reversed --kind decision
```

### Export

```bash
python -m decisionlog export                    # Markdown to stdout
python -m decisionlog export -o log.md
python -m decisionlog export --format json -o log.json
```

---

## Architecture

```
Transcript / Notes
        │
        ▼
┌────────────────────────────┐
│   Extractor (LLM)          │  strict decisions + ownership rules
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│   Deadline Normalizer      │  “next Friday” → concrete date
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│   Decision Store (SQLite)  │  meetings · decisions · actions
└────────────┬───────────────┘
             │
             ▼
   CLI: extract · list · show · status · export
```

Design principles: structured output first, evidence on every item, re-runnable, local-first, focused code.

---

## Project Structure

```
src/decisionlog/
├── cli.py           # extract / list / show / status / export
├── extractor.py     # LLM + ownership rules
├── dates.py         # relative deadline → date
├── models.py        # Pydantic models
└── store.py         # SQLite + re-run + export
```

---

## Roadmap (paused)

**Done (0.2.1)**  
Deadline normalization · ownership cleanup · re-run/replace · status updates · show · meeting filter · Markdown + JSON export

**Later (when we pick it up again)**  
Fuzzy re-run matching · Slack/Teams bot · Notion/Linear push · shared team log

---

## Tech Stack

Python 3.11+ · Pydantic · SQLite · OpenAI-compatible APIs · Typer · python-dateutil · Rich

## License

MIT

Built as a real product experiment — not a toy demo.
