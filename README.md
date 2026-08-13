# DecisionLog

**Turn messy meeting notes into a living decision log.**

Most meeting tools capture *what was said*.  
DecisionLog captures **what was decided**, **who owns it**, and **when it is due** — then keeps it searchable and updatable.

**Current version: 0.5.0**

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
5. **digest** · **assign** · **search** · overdue / due-soon / unassigned
6. Export **Markdown · JSON · CSV · ICS** (calendar)
7. Works with any **OpenAI-compatible** provider via `--base-url`

---

## Quick Start

```bash
git clone https://github.com/VSBhargav5/DecisionLog.git
cd DecisionLog
pip install -e ".[dev]"
pytest -q

export OPENAI_API_KEY="sk-..."
python -m decisionlog extract examples/sample_meeting.txt \
  -m "Sprint Planning 31 Jul" --date 2026-07-31
```

### Day-to-day

```bash
python -m decisionlog digest --days 7
python -m decisionlog list actions --overdue
python -m decisionlog list actions --due-soon 3
python -m decisionlog list actions --unassigned
python -m decisionlog assign <id> Sarah
python -m decisionlog export -f ics -o actions.ics --open-only
python -m decisionlog export -f csv -o actions.csv
```

---

## Status

**v0.5.0** — assign, ICS calendar export, CSV export  
**v0.4.0** — digest, due-soon, unassigned, delete-meeting  
**v0.3.0** — overdue, search, offline tests, CI  
**v0.2.x** — extract, replace, status, export, OpenAI-compatible base URL

---

## Tech

Python 3.11+ · Pydantic · SQLite · OpenAI-compatible APIs · Typer · python-dateutil · Rich

## License

MIT
