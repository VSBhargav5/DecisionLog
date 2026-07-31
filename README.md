# DecisionLog

**Turn messy meeting notes into a living decision log.**

Most meeting tools capture *what was said*.  
DecisionLog captures **what was decided**, **who owns it**, and **when it is due** — then keeps it searchable forever.

---

## The Real Pain

After almost every meeting:

- Decisions get buried in long transcripts or Notion pages
- Action items are written down but ownership is fuzzy (“someone should…”) 
- Deadlines are vague (“next week”) or missing
- Three weeks later nobody remembers *why* a decision was made or who is accountable

Existing tools either:
- Dump the full transcript (noise)
- Extract generic “action items” with weak ownership
- Require manual structuring that nobody does consistently

**DecisionLog solves the overlooked middle layer**: reliable extraction of *decisions* + *owned actions* into a clean, queryable log.

---

## What it does

1. Takes a meeting transcript or notes (plain text / markdown)
2. Uses an LLM to extract:
   - **Decisions** (what was actually decided, not just discussed)
   - **Action items** with clear owners and deadlines
   - Confidence scores and supporting evidence from the text
3. Stores everything in a local decision log (SQLite)
4. Lets you list, search, and update status later

---

## Why this can become a product

- Every knowledge worker has this pain multiple times per week
- High willingness to pay for “decisions that don’t disappear”
- Natural expansion path:
  - Slack / Teams / Zoom bot
  - Notion / Linear / Jira push
  - Team shared decision logs
  - Decision impact tracking over time
- The hard part is reliable extraction + ownership resolution — not the UI

---

## Architecture (v0.1)

```
Transcript / Notes
        │
        ▼
┌───────────────────────┐
│   Extractor (LLM)     │  ← Structured output + evidence
│  - Decisions          │
│  - Action Items       │
│  - Owners & Deadlines │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│   Decision Store      │  ← SQLite (local, simple, portable)
│  - decisions          │
│  - action_items       │
│  - meeting metadata   │
└───────────────────────┘
            │
            ▼
      CLI / Python API
```

Design principles:
- **Structured output first** (not free-form text)
- **Evidence linked** to every extracted item
- **Idempotent-ish** – re-running on the same meeting updates rather than duplicates blindly
- **Local-first** – works offline once the model call is done
- Minimal dependencies

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/VSBhargav5/DecisionLog.git
cd DecisionLog
pip install -r requirements.txt
```

### 2. Set your LLM key

```bash
export OPENAI_API_KEY="sk-..."          # or
export ANTHROPIC_API_KEY="..."          # or use any OpenAI-compatible endpoint
```

(You can also pass `--model` and base URL later.)

### 3. Extract from a meeting

```bash
python -m decisionlog extract path/to/meeting_notes.txt --meeting "Sprint Planning 31 Jul"
```

### 4. View the decision log

```bash
python -m decisionlog list
python -m decisionlog list --status open
```

---

## Example

**Input (meeting notes):**
```text
We discussed the new onboarding flow.
After debate, we decided to drop the phone verification step for now.
Sarah will own the implementation and ship it by next Friday.
John will update the analytics dashboard to track drop-off.
We also agreed that the pricing page experiment stays live for another two weeks.
```

**Extracted:**

**Decisions**
- Drop phone verification step from onboarding (for now)
- Keep pricing page experiment live for another two weeks

**Action Items**
- Sarah → Implement removal of phone verification → Due: next Friday
- John → Update analytics dashboard for drop-off tracking → Due: (none specified)

---

## Project Structure

```
DecisionLog/
├── README.md
├── requirements.txt
├── pyproject.toml
├── src/
│   └── decisionlog/
│       ├── __init__.py
│       ├── __main__.py          # CLI entry
│       ├── extractor.py         # LLM extraction + structured output
│       ├── models.py            # Pydantic models
│       ├── store.py             # SQLite persistence
│       └── cli.py
├── examples/
│   └── sample_meeting.txt
└── tests/
```

---

## Roadmap (honest)

**v0.1 (this)**  
Core extraction + local store + CLI

**v0.2**  
Better ownership resolution, deadline normalization, re-run / update logic, export to Markdown/JSON

**v0.3**  
Simple web UI + shared team log

**Later**  
Slack bot, Notion sync, decision status workflows, impact tracking

---

## Tech Stack

- Python 3.11+
- Pydantic (structured output)
- SQLite (zero-config store)
- OpenAI / Anthropic / any OpenAI-compatible API
- Typer (CLI)

---

## License

MIT – use it, fork it, build on it.

---

Built as a real product experiment, not a toy demo.  
The goal is a tool people would actually open every week after meetings.
