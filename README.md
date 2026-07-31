# DecisionLog

**Turn messy meeting notes into a living decision log.**

Most meeting tools capture *what was said*.  
DecisionLog captures **what was decided**, **who owns it**, and **when it is due** — then keeps it searchable and updatable.

---

## The Real Pain

After almost every meeting:

- Decisions get buried in long transcripts or Notion pages
- Action items are written down but ownership is fuzzy (“someone should…”) 
- Deadlines are vague (“next week”) or missing
- Three weeks later nobody remembers *why* a decision was made or who is accountable

Existing tools either dump the full transcript, extract weak action items, or require manual structuring that nobody maintains.

**DecisionLog focuses on the overlooked middle layer**: reliable extraction of *decisions* + *owned actions* into a clean, queryable, updatable log.

---

## What it does (v0.2)

1. Takes a meeting transcript or notes
2. Uses an LLM to extract:
   - **Decisions** (only what was actually decided)
   - **Action items** with explicit owners and deadlines
   - Evidence quotes + confidence scores
3. **Normalizes relative deadlines** (“next Friday”, “end of month”, “in 2 weeks”) into concrete dates
4. Stores everything in a local SQLite decision log
5. Supports **re-running** extraction on the same meeting (replace mode)
6. Lets you **update status** of actions/decisions and **export** to Markdown

---

## Why this can become a product

- Every knowledge worker hits this pain multiple times per week
- High willingness to pay for “decisions that don’t disappear”
- Natural expansion path: Slack/Teams bot → Notion/Linear push → shared team logs → impact tracking
- The hard part is reliable extraction + ownership + deadline handling — not the UI

---

## Architecture

```
Transcript / Notes
        │
        ▼
┌────────────────────────────┐
│   Extractor (LLM)          │
│  - Strict decision rules   │
│  - Ownership resolution    │
│  - Deadline phrases        │
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│   Deadline Normalizer      │  ← “next Friday” → 2026-08-07
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│   Decision Store (SQLite)  │
│  - meetings                │
│  - decisions + status      │
│  - action items + owner    │
└────────────┬───────────────┘
             │
             ▼
      CLI (extract / list / status / export)
```

Design principles:
- Structured output first
- Evidence linked to every item
- Re-runnable (replace mode for the same meeting title)
- Local-first
- Focused code, no bloat

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

Re-run / replace an existing meeting:

```bash
python -m decisionlog extract examples/sample_meeting.txt \
  -m "Sprint Planning 31 Jul" \
  --date 2026-07-31 \
  --replace
```

### List

```bash
python -m decisionlog list actions
python -m decisionlog list actions --status open --owner Sarah
python -m decisionlog list decisions
python -m decisionlog list meetings
```

### Update status

```bash
# Use full ID or first 8 characters
python -m decisionlog status <id> done
python -m decisionlog status <id> in_progress --owner Sarah
python -m decisionlog status <id> reversed --kind decision
```

### Export Markdown

```bash
python -m decisionlog export
python -m decisionlog export -o decision_log.md
```

---

## Example

**Input:**
```text
We decided to remove mandatory phone verification.
Sarah will own the implementation and ship it by next Friday.
John will update the analytics dashboard.
We agreed the pricing experiment stays live for another two weeks.
```

**Result:**
- Decisions: remove mandatory phone verification; keep pricing experiment live another two weeks
- Actions:
  - Sarah → implement removal → due: concrete date (normalized from “next Friday”)
  - John → update analytics dashboard

---

## Project Structure

```
src/decisionlog/
├── __init__.py
├── __main__.py
├── cli.py              # extract / list / status / export
├── extractor.py        # LLM + ownership rules
├── dates.py            # relative deadline → concrete date
├── models.py           # Pydantic models
└── store.py            # SQLite + re-run + status + markdown export
```

---

## Roadmap

**v0.2 (current)**  
Deadline normalization • ownership cleanup • re-run/replace • status updates • Markdown export

**v0.3**  
Better fuzzy matching on re-run • JSON export • simple filters by date range

**Later**  
Slack bot, Notion/Linear sync, shared team log, decision impact tracking

---

## Tech Stack

Python 3.11+ • Pydantic • SQLite • OpenAI-compatible APIs • Typer • python-dateutil • Rich

---

## License

MIT

Built as a real product experiment — not a toy demo.
