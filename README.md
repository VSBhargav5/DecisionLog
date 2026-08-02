# DecisionLog

**Turn messy meeting notes into a living decision log.**

Most meeting tools capture *what was said*.  
DecisionLog captures **what was decided**, **who owns it**, and **when it is due** — then keeps it searchable and updatable.

**Current version: 0.2.2** — solid local-first CLI. On hold until the next focused product push (PromptGuard next).

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
2. Uses an LLM to extract clear **decisions** and **action items** (owners, deadlines, evidence, confidence)
3. **Normalizes relative deadlines** (`by next Friday`, `EOD`, `end of month`, `in 2 weeks`, …)
4. Stores everything in local SQLite
5. **Re-run / replace** on the same meeting title
6. **Status updates**, **show**, **list filters**, **Markdown + JSON export**
7. Works with any **OpenAI-compatible** provider via `--base-url`

---

## Quick Start

```bash
git clone https://github.com/VSBhargav5/DecisionLog.git
cd DecisionLog
pip install -r requirements.txt

export OPENAI_API_KEY="sk-..."
```

Other providers (Groq, Together, local gateways, etc.):

```bash
export OPENAI_API_KEY="your-key"
python -m decisionlog extract notes.txt -m "Standup" \
  --base-url https://api.groq.com/openai/v1 \
  --model llama-3.3-70b-versatile
```

### Extract

```bash
python -m decisionlog extract examples/sample_meeting.txt \
  -m "Sprint Planning 31 Jul" \
  --date 2026-07-31

# Messier real-world style notes
python -m decisionlog extract examples/messy_standup.txt \
  -m "Daily standup Aug 1" \
  --date 2026-08-01
```

Re-run (overwrite):

```bash
python -m decisionlog extract examples/sample_meeting.txt \
  -m "Sprint Planning 31 Jul" --date 2026-07-31 --replace
```

### List / show / status / export

```bash
python -m decisionlog list actions --status open --owner Sarah
python -m decisionlog list actions --meeting "Sprint Planning 31 Jul"
python -m decisionlog show <id>
python -m decisionlog status <id> done
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
│   Deadline Normalizer      │  “by next Friday” → concrete date
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

---

## Project Structure

```
src/decisionlog/
├── cli.py           # extract / list / show / status / export
├── extractor.py     # LLM + ownership rules
├── dates.py         # relative deadline → date
├── models.py
└── store.py         # SQLite + re-run + export
examples/
├── sample_meeting.txt
└── messy_standup.txt   # harder, more realistic notes
```

---

## Status

**v0.2.2 (current)** — polish pass: MIT license, `--base-url`, better deadline phrases, clearer API errors, second sample.

**Paused** — next major portfolio project is **PromptGuard** (LLM behavior regression tester).

---

## Tech Stack

Python 3.11+ · Pydantic · SQLite · OpenAI-compatible APIs · Typer · python-dateutil · Rich

## License

MIT
