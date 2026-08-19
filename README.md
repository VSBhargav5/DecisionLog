# DecisionLog

**Turn messy meeting notes into a living decision log.**

Most meeting tools capture *what was said*.  
DecisionLog captures **what was decided**, **who owns it**, **when it is due**, and **what is still blocking this week** — then hands you a paste-ready standup digest.

**Current version: 0.7.0**

---

## The Real Pain

After almost every meeting:

- Decisions get buried in long transcripts
- Action items lack clear ownership
- Deadlines are vague (“next week”) or missing
- Monday standup has no single artifact of *what is still true*

DecisionLog is the overlooked middle layer: extract decisions + owned actions, then **keep the log honest** with a weekly digest people actually paste.

---

## What it does

1. Takes meeting notes / transcript
2. Extracts **decisions** and **action items** (owners, deadlines, evidence, confidence)
3. **Normalizes relative deadlines** (`by next Friday`, `EOD`, `end of month`, …)
4. Stores everything in local SQLite
5. Day-to-day: **digest · done · due · priority · tag · note · assign · stats**
6. **Weekly digest** — critical P0/P1 overdue, due soon, unassigned, owner load, decisions this window  
   Formats: terminal · **Markdown** · **Slack** · JSON
7. Export **Markdown · JSON · CSV · ICS**
8. Any **OpenAI-compatible** provider via `--base-url`

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

### The weekly artifact (v0.7)

```bash
# Terminal
python -m decisionlog digest --days 7

# Paste into Notion / email
python -m decisionlog digest -f md -o standup.md

# Paste into Slack
python -m decisionlog digest -f slack
```

### Day-to-day

```bash
python -m decisionlog list actions --overdue
python -m decisionlog list actions --priority P0
python -m decisionlog done <id>
python -m decisionlog due <id> 2026-08-22
python -m decisionlog priority <id> P0
python -m decisionlog assign <id> Sarah
python -m decisionlog export -f ics -o actions.ics --open-only
```

---

## Status

**v0.7.0** — weekly digest as a first-class artifact (`md` / `slack` / `json`), critical P0/P1 slice  
**v0.6.0** — priority, tags, notes, `done` / `due` / `priority` / `tag` / `note` / `reopen` / `stats`  
**v0.5.0** — assign, ICS / CSV export  
**v0.4.0** — digest, due-soon, unassigned, delete-meeting  
**v0.3.0** — overdue, search, offline tests, CI  
**v0.2.x** — extract, replace, status, export, OpenAI-compatible base URL

---

## Tech

Python 3.11+ · Pydantic · SQLite · OpenAI-compatible APIs · Typer · python-dateutil · Rich

## License

MIT
