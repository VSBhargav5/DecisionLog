# DecisionLog

**Turn messy meeting notes into a living decision log.**

Most meeting tools capture *what was said*.  
DecisionLog captures **what was decided**, **who owns it**, and **when it is due** — then keeps it searchable and updatable.

**Current version: 0.3.0**

---

## The Real Pain

After almost every meeting:

- Decisions get buried in long transcripts
- Action items lack clear ownership
- Deadlines are vague (“next week”) or missing
- Weeks later nobody remembers *why* a call was made

DecisionLog focuses on the overlooked middle layer: reliable extraction of **decisions** + **owned actions** into a queryable log.

---

## What it does

1. Takes meeting notes / transcript
2. Extracts **decisions** and **action items** (owners, deadlines, evidence, confidence)
3. **Normalizes relative deadlines** (`by next Friday`, `EOD`, `end of month`, …)
4. Stores everything in local SQLite
5. **Re-run / replace**, **status updates**, **search**, **overdue list**, **Markdown + JSON export**
6. Works with any **OpenAI-compatible** provider via `--base-url`

---

## Quick Start

```bash
git clone https://github.com/VSBhargav5/DecisionLog.git
cd DecisionLog
pip install -e ".[dev]"

pytest -q   # offline, no API key

export OPENAI_API_KEY="sk-..."
python -m decisionlog extract examples/sample_meeting.txt \
  -m "Sprint Planning 31 Jul" --date 2026-07-31
```

### List / search / overdue

```bash
python -m decisionlog list actions --status open --owner Sarah
python -m decisionlog list actions --overdue
python -m decisionlog search refund
python -m decisionlog show <id>
python -m decisionlog status <id> done
python -m decisionlog export -o log.md
```

---

## Architecture

```
Transcript → LLM extractor → deadline normalizer → SQLite store
                ↓
     extract · list · search · show · status · export
```

---

## Status

**v0.3.0** — overdue filter, search, offline unit tests, GitHub Actions CI  
**v0.2.x** — extract, replace, status, export, OpenAI-compatible base URL

---

## Tech

Python 3.11+ · Pydantic · SQLite · OpenAI-compatible APIs · Typer · python-dateutil · Rich

## License

MIT
