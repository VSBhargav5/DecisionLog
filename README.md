# DecisionLog

**Turn messy meeting notes into a living decision log.**

Most meeting tools capture *what was said*.  
DecisionLog captures **what was decided**, **who owns it**, **when it is due**, and **what is still blocking this week** — then hands you paste-ready standup artifacts and a personal **today** board.

**Current version: 0.8.0**

---

## The Real Pain

After almost every meeting:

- Decisions get buried in long transcripts
- Action items lack clear ownership
- Deadlines are vague (“next week”) or missing
- Monday standup has no single artifact of *what is still true*
- Nobody knows what is **blocked**, **stale**, or **due today for me**

DecisionLog is the overlooked middle layer: extract decisions + owned actions, keep the log honest with digests people actually paste, and give each person a board for the day.

---

## What it does (v0.8)

1. Takes meeting notes / transcript (or **CSV import**)
2. Extracts **decisions** and **action items** (owners, deadlines, evidence, confidence)
3. **Normalizes relative deadlines** (`by next Friday`, `EOD`, …) + **snooze**
4. Stores everything in local SQLite with an **activity log**
5. Day-to-day: **digest · today · block · snooze · history · archive**
6. **Weekly digest** — critical P0/P1, due today, stale, completed this window, owner load  
   Formats: terminal · **Markdown** · **Slack** · **HTML** · JSON
7. **Today board** — personal overdue / due today / blocked / in progress
8. Export **Markdown · JSON · CSV · ICS**
9. Optional `~/.decisionlog/config.json` for **owner aliases**

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

### Weekly artifact

```bash
python -m decisionlog digest --days 7
python -m decisionlog digest -f md -o standup.md
python -m decisionlog digest -f slack
python -m decisionlog digest -f html -o standup.html
```

### Personal today board

```bash
python -m decisionlog today Sarah
python -m decisionlog today Sarah -f md -o my-day.md
```

### Flow control

```bash
python -m decisionlog block <id> "waiting on legal"
python -m decisionlog unblock <id>
python -m decisionlog snooze <id> 3
python -m decisionlog history
python -m decisionlog archive --older-than 30
python -m decisionlog import-csv examples/actions_import.csv -m "Backlog import"
```

---

## Status

**v0.8.0** — today board, blocked/stale, activity history, HTML digest, CSV import, snooze, archive  
**v0.7.0** — weekly digest as a first-class artifact (`md` / `slack` / `json`)  
**v0.6.0** — priority, tags, notes, ops CLI  
**v0.5.0** — assign, ICS / CSV export  
**v0.4.0** — digest, due-soon, unassigned  
**v0.3.0** — overdue, search, offline tests, CI

---

## Tech

Python 3.11+ · Pydantic · SQLite · OpenAI-compatible APIs · Typer · python-dateutil · Rich

## License

MIT
