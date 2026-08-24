# Changelog

## 0.8.0 — 2026-08-24

### Added
- **Today board** (`today <owner>`) — overdue, due today, blocked, in progress
- **Activity log** — every action/decision mutation recorded; `history` command
- **Blocked** status + `block` / `unblock` with reason
- **Stale** detection (no update in 14d) in digest + stats
- **Completed this window** in digest
- **HTML digest** (`digest -f html`)
- **CSV import** (`import-csv`)
- **Snooze** due dates
- **Archive** old done items
- Owner name normalization + config sample for aliases
- `Makefile`, progress helpers (`start`/`finish`)

### Changed
- Digest markdown/slack include due-today, blocked counts, stale, completed
- Stats include blocked, completed_7d, stale_14d

## 0.7.0

- Weekly digest as first-class artifact (`md` / `slack` / `json`), critical P0/P1 slice

## 0.6.0

- Priority, tags, notes, day-to-day ops CLI
