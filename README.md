# DecisionLog

**Turn messy meeting notes into a living decision log.**

Most meeting tools capture *what was said*.  
DecisionLog captures **what was decided**, **who owns it**, **when it is due**, and now **priority / tags / notes** — then keeps it searchable and updatable.

**Current version: 0.6.0**

---

## The Real Pain

After almost every meeting:

- Decisions get buried in long transcripts
- Action items lack clear ownership
- Deadlines are vague (“next week”) or missing
- Weeks later nobody remembers *why* a call was made

DecisionLog focuses on the overlooked middle layer: reliable extraction of **decisions** + **owned actions** into a queryable log you actually maintain.

---

## What it does

1. Takes meeting notes / transcript
2. Extracts **decisions** and **action items** (owners, deadlines, evidence, confidence)
3. **Normalizes relative deadlines** (`by next Friday`, `EOD`, `end of month`, …)
4. Stores everything in local SQLite
5. Day-to-day ops: **digest · done · due · priority · tag · note · assign · stats**
6. Filters: overdue / due-soon / unassigned / priority / tag
7. Export **Markdown · JSON · CSV · ICS** (calendar)
8. Works with any **OpenAI-compatible** provider via `--base-url`

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

### Day-to-day (v0.6)

```bash
python -m decisionlog digest --days 7
python -m decisionlog stats
python -m decisionlog list actions --overdue
python -m decisionlog list actions --priority P0
python -m decisionlog list actions --tag infra

python -m decisionlog done <id>
python -m decisionlog due <id> 2026-08-22
python -m decisionlog priority <id> P0
python -m decisionlog tag <id> infra,urgent
python -m decisionlog note <id> "Blocked on legal review"
python -m decisionlog assign <id> Sarah
python -m decisionlog reopen <id>

python -m decisionlog export -f ics -o actions.ics --open-only
python -m decisionlog export -f csv -o actions.csv
```

---

## Status

**v0.6.0** — priority (P0–P3), tags, notes, `done` / `due` / `priority` / `tag` / `note` / `reopen` / `stats`  
**v0.5.0** — assign, ICS calendar export, CSV export  
**v0.4.0** — digest, due-soon, unassigned, delete-meeting  
**v0.3.0** — overdue, search, offline tests, CI  
**v0.2.x** — extract, replace, status, export, OpenAI-compatible base URL

---

## Tech

Python 3.11+ · Pydantic · SQLite · OpenAI-compatible APIs · Typer · python-dateutil · Rich

## License

MIT
