from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .models import ActionPriority, ActionStatus, DecisionStatus, ExtractionResult
from .owners import normalize_owner


DEFAULT_DB = Path.home() / ".decisionlog" / "decisions.db"

ACTIVE_STATUSES = ("open", "in_progress", "blocked")
CLOSED_STATUSES = ("done", "cancelled", "archived")


def _tags_to_str(tags: list[str] | None) -> str:
    if not tags:
        return ""
    cleaned = sorted({t.strip().lower() for t in tags if t and t.strip()})
    return ",".join(cleaned)


def _tags_from_str(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [t for t in (x.strip() for x in raw.split(",")) if t]


def _action_priority(action: dict) -> str:
    return (action.get("priority") or "P2").upper()


class DecisionStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS meetings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT,
                    meeting_date TEXT,
                    source_path TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    meeting_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    evidence TEXT,
                    confidence REAL,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
                );

                CREATE TABLE IF NOT EXISTS action_items (
                    id TEXT PRIMARY KEY,
                    meeting_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    owner TEXT,
                    due_date TEXT,
                    due_text TEXT,
                    status TEXT NOT NULL,
                    priority TEXT DEFAULT 'P2',
                    tags TEXT DEFAULT '',
                    notes TEXT,
                    blocked_reason TEXT,
                    evidence TEXT,
                    confidence REAL,
                    linked_decision_id TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
                );

                CREATE TABLE IF NOT EXISTS activity_log (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_meetings_title ON meetings(title);
                CREATE INDEX IF NOT EXISTS idx_decisions_meeting ON decisions(meeting_id);
                CREATE INDEX IF NOT EXISTS idx_actions_meeting ON action_items(meeting_id);
                CREATE INDEX IF NOT EXISTS idx_actions_status ON action_items(status);
                CREATE INDEX IF NOT EXISTS idx_actions_owner ON action_items(owner);
                CREATE INDEX IF NOT EXISTS idx_actions_due ON action_items(due_date);
                CREATE INDEX IF NOT EXISTS idx_actions_priority ON action_items(priority);
                CREATE INDEX IF NOT EXISTS idx_activity_entity ON activity_log(entity_id, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_log(created_at DESC);
                """
            )
            self._migrate(conn)

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Add columns introduced after earlier versions without breaking existing DBs."""
        cols = {
            r[1] for r in conn.execute("PRAGMA table_info(action_items)").fetchall()
        }
        if "priority" not in cols:
            conn.execute("ALTER TABLE action_items ADD COLUMN priority TEXT DEFAULT 'P2'")
        if "tags" not in cols:
            conn.execute("ALTER TABLE action_items ADD COLUMN tags TEXT DEFAULT ''")
        if "notes" not in cols:
            conn.execute("ALTER TABLE action_items ADD COLUMN notes TEXT")
        if "blocked_reason" not in cols:
            conn.execute("ALTER TABLE action_items ADD COLUMN blocked_reason TEXT")

        mcols = {r[1] for r in conn.execute("PRAGMA table_info(meetings)").fetchall()}
        if "source_path" not in mcols:
            conn.execute("ALTER TABLE meetings ADD COLUMN source_path TEXT")

    def log_activity(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        detail: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO activity_log (id, entity_type, entity_id, action, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    entity_type,
                    entity_id,
                    action,
                    detail,
                    datetime.utcnow().isoformat(),
                ),
            )

    def list_activity(
        self,
        *,
        entity_id: str | None = None,
        limit: int = 40,
    ) -> list[dict]:
        query = "SELECT * FROM activity_log"
        params: list = []
        if entity_id:
            query += " WHERE entity_id = ? OR entity_id LIKE ?"
            params.extend([entity_id, f"{entity_id}%"])
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def _row_action(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        d["tags"] = _tags_from_str(d.get("tags"))
        d.setdefault("priority", "P2")
        return d

    def find_meeting_by_title(self, title: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM meetings WHERE title = ? ORDER BY created_at DESC LIMIT 1",
                (title,),
            ).fetchone()
            return dict(row) if row else None

    def get_meeting(self, meeting_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM meetings WHERE id = ?", (meeting_id,)
            ).fetchone()
            return dict(row) if row else None

    def resolve_meeting(self, title_or_id: str) -> Optional[dict]:
        m = self.find_meeting_by_title(title_or_id)
        if m:
            return m
        m = self.get_meeting(title_or_id)
        if m:
            return m
        for row in self.list_meetings():
            if row["id"].startswith(title_or_id):
                return row
        return None

    def delete_meeting(self, meeting_id: str) -> bool:
        with self._connect() as conn:
            conn.execute("DELETE FROM decisions WHERE meeting_id = ?", (meeting_id,))
            conn.execute("DELETE FROM action_items WHERE meeting_id = ?", (meeting_id,))
            cur = conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
            ok = cur.rowcount > 0
        if ok:
            self.log_activity("meeting", meeting_id, "deleted")
        return ok

    def save_extraction(
        self,
        meeting_id: str,
        title: str,
        result: ExtractionResult,
        *,
        meeting_date: Optional[date] = None,
        replace_existing: bool = False,
        source_path: Optional[str] = None,
    ) -> str:
        now = datetime.utcnow().isoformat()
        existing = self.find_meeting_by_title(title)

        if replace_existing and existing:
            meeting_id = existing["id"]
            with self._connect() as conn:
                conn.execute("DELETE FROM decisions WHERE meeting_id = ?", (meeting_id,))
                conn.execute("DELETE FROM action_items WHERE meeting_id = ?", (meeting_id,))
                conn.execute(
                    """
                    UPDATE meetings
                    SET summary = ?, meeting_date = ?, source_path = COALESCE(?, source_path),
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        result.meeting_summary,
                        meeting_date.isoformat() if meeting_date else existing.get("meeting_date"),
                        source_path,
                        now,
                        meeting_id,
                    ),
                )
            self.log_activity("meeting", meeting_id, "replaced", title)
        else:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO meetings
                    (id, title, summary, meeting_date, source_path, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        meeting_id,
                        title,
                        result.meeting_summary,
                        meeting_date.isoformat() if meeting_date else None,
                        source_path,
                        now,
                        now,
                    ),
                )
            self.log_activity("meeting", meeting_id, "created", title)

        with self._connect() as conn:
            for d in result.decisions:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO decisions
                    (id, meeting_id, text, status, evidence, confidence, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d.id,
                        meeting_id,
                        d.text,
                        d.status.value,
                        d.evidence,
                        d.confidence,
                        d.created_at.isoformat(),
                        d.updated_at.isoformat(),
                    ),
                )

            for a in result.action_items:
                priority = a.priority.value if hasattr(a.priority, "value") else (a.priority or "P2")
                owner = normalize_owner(a.owner)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO action_items
                    (id, meeting_id, text, owner, due_date, due_text, status,
                     priority, tags, notes, blocked_reason, evidence, confidence,
                     linked_decision_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        a.id,
                        meeting_id,
                        a.text,
                        owner,
                        a.due_date.isoformat() if a.due_date else None,
                        a.due_text,
                        a.status.value,
                        priority,
                        _tags_to_str(a.tags),
                        a.notes,
                        a.blocked_reason,
                        a.evidence,
                        a.confidence,
                        a.linked_decision_id,
                        a.created_at.isoformat(),
                        a.updated_at.isoformat(),
                    ),
                )

        return meeting_id

    def list_decisions(
        self,
        status: Optional[str] = None,
        meeting_id: Optional[str] = None,
    ) -> list[dict]:
        query = (
            "SELECT d.*, m.title AS meeting_title "
            "FROM decisions d JOIN meetings m ON d.meeting_id = m.id"
        )
        clauses: list[str] = []
        params: list = []
        if status:
            clauses.append("d.status = ?")
            params.append(status)
        if meeting_id:
            clauses.append("d.meeting_id = ?")
            params.append(meeting_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY d.created_at DESC"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def list_actions(
        self,
        status: Optional[str] = None,
        owner: Optional[str] = None,
        meeting_id: Optional[str] = None,
        *,
        overdue: bool = False,
        due_within_days: Optional[int] = None,
        due_on: Optional[date] = None,
        unassigned: bool = False,
        priority: Optional[str] = None,
        tag: Optional[str] = None,
        blocked_only: bool = False,
        include_closed: bool = False,
        as_of: Optional[date] = None,
    ) -> list[dict]:
        query = (
            "SELECT a.*, m.title AS meeting_title "
            "FROM action_items a JOIN meetings m ON a.meeting_id = m.id"
        )
        clauses: list[str] = []
        params: list = []
        today = as_of or date.today()

        if status:
            clauses.append("a.status = ?")
            params.append(status)
        elif not include_closed and not overdue and due_within_days is None and due_on is None:
            # default list still shows active + done unless filters imply otherwise
            pass
        if owner:
            clauses.append("LOWER(a.owner) = LOWER(?)")
            params.append(owner)
        if meeting_id:
            clauses.append("a.meeting_id = ?")
            params.append(meeting_id)
        if priority:
            clauses.append("UPPER(IFNULL(a.priority, 'P2')) = UPPER(?)")
            params.append(priority)
        if tag:
            clauses.append(
                "(',' || LOWER(IFNULL(a.tags, '')) || ',') LIKE ?"
            )
            params.append(f"%,{tag.strip().lower()},%")
        if unassigned:
            clauses.append("(a.owner IS NULL OR TRIM(a.owner) = '')")
            clauses.append(f"a.status IN ({','.join('?' * len(ACTIVE_STATUSES))})")
            params.extend(ACTIVE_STATUSES)
        if blocked_only:
            clauses.append("a.status = 'blocked'")
        if overdue:
            clauses.append("a.due_date IS NOT NULL")
            clauses.append("a.due_date < ?")
            params.append(today.isoformat())
            clauses.append(f"a.status IN ({','.join('?' * len(ACTIVE_STATUSES))})")
            params.extend(ACTIVE_STATUSES)
        if due_on is not None:
            clauses.append("a.due_date = ?")
            params.append(due_on.isoformat())
            clauses.append(f"a.status IN ({','.join('?' * len(ACTIVE_STATUSES))})")
            params.extend(ACTIVE_STATUSES)
        if due_within_days is not None:
            end = today + timedelta(days=due_within_days)
            clauses.append("a.due_date IS NOT NULL")
            clauses.append("a.due_date >= ?")
            clauses.append("a.due_date <= ?")
            params.extend([today.isoformat(), end.isoformat()])
            clauses.append(f"a.status IN ({','.join('?' * len(ACTIVE_STATUSES))})")
            params.extend(ACTIVE_STATUSES)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        if overdue or due_within_days is not None or due_on is not None:
            query += " ORDER BY a.due_date ASC, IFNULL(a.priority, 'P2') ASC"
        else:
            query += " ORDER BY IFNULL(a.priority, 'P2') ASC, a.created_at DESC"
        with self._connect() as conn:
            return [self._row_action(r) for r in conn.execute(query, params).fetchall()]

    def list_meetings(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM meetings ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def recent_decisions(
        self,
        *,
        since: date,
        status: str = "decided",
        limit: int = 20,
    ) -> list[dict]:
        rows = self.list_decisions(status=status)
        out: list[dict] = []
        for d in rows:
            created = str(d.get("created_at") or "")[:10]
            try:
                created_d = date.fromisoformat(created)
            except ValueError:
                continue
            if created_d >= since:
                out.append(d)
            if len(out) >= limit:
                break
        return out

    def completed_since(self, since: date, *,
                        limit: int = 50) -> list[dict]:
        """Actions marked done/cancelled on or after since (by updated_at)."""
        out: list[dict] = []
        for a in self.list_actions(include_closed=True):
            if a.get("status") not in ("done", "cancelled"):
                continue
            updated = str(a.get("updated_at") or "")[:10]
            try:
                u = date.fromisoformat(updated)
            except ValueError:
                continue
            if u >= since:
                out.append(a)
            if len(out) >= limit:
                break
        return out

    def stale_actions(
        self,
        *,
        days: int = 14,
        as_of: Optional[date] = None,
    ) -> list[dict]:
        """Active actions with no update in `days` days."""
        today = as_of or date.today()
        cutoff = today - timedelta(days=max(days, 0))
        out: list[dict] = []
        for a in self.list_actions(status="open") + self.list_actions(status="in_progress") + self.list_actions(status="blocked"):
            updated = str(a.get("updated_at") or a.get("created_at") or "")[:10]
            try:
                u = date.fromisoformat(updated)
            except ValueError:
                continue
            if u < cutoff:
                out.append(a)
        return out

    def digest(
        self,
        *,
        due_within_days: int = 7,
        stale_days: int = 14,
        as_of: Optional[date] = None,
    ) -> dict:
        today = as_of or date.today()
        window_start = today - timedelta(days=max(due_within_days, 0))
        open_actions = self.list_actions(status="open")
        in_progress = self.list_actions(status="in_progress")
        blocked = self.list_actions(status="blocked")
        overdue = self.list_actions(overdue=True, as_of=today)
        due_soon = self.list_actions(due_within_days=due_within_days, as_of=today)
        due_today = self.list_actions(due_on=today, as_of=today)
        unassigned = self.list_actions(unassigned=True)
        decisions = self.list_decisions(status="decided")
        meetings = self.list_meetings()
        recent = self.recent_decisions(since=window_start)
        completed = self.completed_since(window_start)
        stale = self.stale_actions(days=stale_days, as_of=today)

        by_owner: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for a in open_actions + in_progress + blocked:
            key = (a.get("owner") or "(unassigned)").strip() or "(unassigned)"
            by_owner[key] = by_owner.get(key, 0) + 1
            p = _action_priority(a)
            by_priority[p] = by_priority.get(p, 0) + 1

        critical = [a for a in overdue if _action_priority(a) in {"P0", "P1"}]
        p0_open = [a for a in open_actions + in_progress + blocked if _action_priority(a) == "P0"]

        return {
            "as_of": today.isoformat(),
            "window_start": window_start.isoformat(),
            "window_days": due_within_days,
            "stale_days": stale_days,
            "meetings": len(meetings),
            "decisions_decided": len(decisions),
            "actions_open": len(open_actions),
            "actions_in_progress": len(in_progress),
            "actions_blocked": len(blocked),
            "overdue": overdue,
            "critical": critical,
            "p0_open": p0_open,
            "due_today": due_today,
            "due_soon": due_soon,
            "unassigned": unassigned,
            "stale": stale,
            "completed": completed,
            "recent_decisions": recent,
            "by_owner": dict(sorted(by_owner.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_priority": dict(sorted(by_priority.items())),
        }

    def today_board(
        self,
        owner: str,
        *,
        as_of: Optional[date] = None,
    ) -> dict:
        """Personal view: due today, overdue, blocked, in progress for one owner."""
        today = as_of or date.today()
        mine = self.list_actions(owner=owner)
        active = [a for a in mine if a.get("status") in ACTIVE_STATUSES]
        overdue = [
            a for a in active
            if a.get("due_date") and str(a["due_date"])[:10] < today.isoformat()
        ]
        due_today = [
            a for a in active
            if a.get("due_date") and str(a["due_date"])[:10] == today.isoformat()
        ]
        blocked = [a for a in active if a.get("status") == "blocked"]
        in_progress = [a for a in active if a.get("status") == "in_progress"]
        open_rest = [
            a for a in active
            if a.get("status") == "open" and a not in overdue and a not in due_today
        ]
        return {
            "owner": owner,
            "as_of": today.isoformat(),
            "overdue": overdue,
            "due_today": due_today,
            "blocked": blocked,
            "in_progress": in_progress,
            "open": open_rest,
        }

    def stats(self, *,
              as_of: Optional[date] = None) -> dict:
        today = as_of or date.today()
        all_actions = self.list_actions(include_closed=True)
        by_status: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for a in all_actions:
            by_status[a["status"]] = by_status.get(a["status"], 0) + 1
            p = _action_priority(a)
            by_priority[p] = by_priority.get(p, 0) + 1
        week_ago = today - timedelta(days=7)
        return {
            "as_of": today.isoformat(),
            "meetings": len(self.list_meetings()),
            "decisions": len(self.list_decisions()),
            "actions": len(all_actions),
            "by_status": by_status,
            "by_priority": by_priority,
            "overdue_count": len(self.list_actions(overdue=True, as_of=today)),
            "unassigned_count": len(self.list_actions(unassigned=True)),
            "blocked_count": len(self.list_actions(status="blocked")),
            "completed_7d": len(self.completed_since(week_ago)),
            "stale_14d": len(self.stale_actions(days=14, as_of=today)),
        }

    def search(self, query: str, limit: int = 30) -> dict[str, list[dict]]:
        q = f"%{query.strip()}%"
        with self._connect() as conn:
            decisions = [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT d.*, m.title AS meeting_title
                    FROM decisions d JOIN meetings m ON d.meeting_id = m.id
                    WHERE d.text LIKE ? OR IFNULL(d.evidence, '') LIKE ?
                    ORDER BY d.created_at DESC LIMIT ?
                    """,
                    (q, q, limit),
                ).fetchall()
            ]
            actions = [
                self._row_action(r)
                for r in conn.execute(
                    """
                    SELECT a.*, m.title AS meeting_title
                    FROM action_items a JOIN meetings m ON a.meeting_id = m.id
                    WHERE a.text LIKE ? OR IFNULL(a.owner, '') LIKE ?
                       OR IFNULL(a.evidence, '') LIKE ?
                       OR IFNULL(a.tags, '') LIKE ?
                       OR IFNULL(a.notes, '') LIKE ?
                       OR IFNULL(a.blocked_reason, '') LIKE ?
                    ORDER BY a.created_at DESC LIMIT ?
                    """,
                    (q, q, q, q, q, q, limit),
                ).fetchall()
            ]
            meetings = [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT * FROM meetings
                    WHERE title LIKE ? OR IFNULL(summary, '') LIKE ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    (q, q, limit),
                ).fetchall()
            ]
        return {"decisions": decisions, "actions": actions, "meetings": meetings}

    def get_decision(self, item_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT d.*, m.title AS meeting_title "
                "FROM decisions d LEFT JOIN meetings m ON d.meeting_id = m.id "
                "WHERE d.id = ?",
                (item_id,),
            ).fetchone()
            return dict(row) if row else None

    def get_action(self, item_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT a.*, m.title AS meeting_title "
                "FROM action_items a LEFT JOIN meetings m ON a.meeting_id = m.id "
                "WHERE a.id = ?",
                (item_id,),
            ).fetchone()
            return self._row_action(row) if row else None

    def resolve_id(self, short_or_full: str, kind: str) -> Optional[dict]:
        if kind == "decision":
            item = self.get_decision(short_or_full)
            if item:
                return item
            for row in self.list_decisions():
                if row["id"].startswith(short_or_full):
                    return row
        else:
            item = self.get_action(short_or_full)
            if item:
                return item
            for row in self.list_actions(include_closed=True):
                if row["id"].startswith(short_or_full):
                    return row
        return None

    def update_decision_status(self, item_id: str, status: str) -> bool:
        try:
            DecisionStatus(status)
        except ValueError:
            return False
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE decisions SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, item_id),
            )
            ok = cur.rowcount > 0
        if ok:
            self.log_activity("decision", item_id, "status", status)
        return ok

    def update_action(
        self,
        item_id: str,
        *,
        status: Optional[str] = None,
        owner: Optional[str] = None,
        priority: Optional[str] = None,
        due_date: Optional[date | str] = None,
        clear_due: bool = False,
        tags: Optional[list[str]] = None,
        notes: Optional[str] = None,
        append_note: Optional[str] = None,
        blocked_reason: Optional[str] = None,
        clear_blocked_reason: bool = False,
    ) -> bool:
        if status:
            try:
                ActionStatus(status)
            except ValueError:
                return False
        if priority:
            try:
                ActionPriority(priority.upper())
                priority = priority.upper()
            except ValueError:
                return False

        sets: list[str] = []
        params: list = []
        details: list[str] = []

        if status:
            sets.append("status = ?")
            params.append(status)
            details.append(f"status={status}")
        if owner is not None:
            owner_n = normalize_owner(owner) if owner else None
            sets.append("owner = ?")
            params.append(owner_n)
            details.append(f"owner={owner_n or 'unassigned'}")
        if priority:
            sets.append("priority = ?")
            params.append(priority)
            details.append(f"priority={priority}")
        if clear_due:
            sets.append("due_date = NULL")
            sets.append("due_text = NULL")
            details.append("due=cleared")
        elif due_date is not None:
            if isinstance(due_date, date):
                iso = due_date.isoformat()
            else:
                iso = str(due_date)[:10]
            sets.append("due_date = ?")
            params.append(iso)
            details.append(f"due={iso}")
        if tags is not None:
            sets.append("tags = ?")
            params.append(_tags_to_str(tags))
            details.append("tags updated")
        if notes is not None:
            sets.append("notes = ?")
            params.append(notes)
            details.append("notes set")
        if append_note:
            existing = self.get_action(item_id)
            if not existing:
                return False
            stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            prev = (existing.get("notes") or "").rstrip()
            line = f"[{stamp}] {append_note.strip()}"
            merged = f"{prev}\n{line}".strip() if prev else line
            sets.append("notes = ?")
            params.append(merged)
            details.append("note appended")
        if clear_blocked_reason:
            sets.append("blocked_reason = NULL")
            details.append("unblocked")
        elif blocked_reason is not None:
            sets.append("blocked_reason = ?")
            params.append(blocked_reason)
            details.append(f"blocked={blocked_reason[:80]}")

        if not sets:
            return False

        sets.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(item_id)

        with self._connect() as conn:
            cur = conn.execute(
                f"UPDATE action_items SET {', '.join(sets)} WHERE id = ?",
                params,
            )
            ok = cur.rowcount > 0
        if ok:
            self.log_activity("action", item_id, "update", "; ".join(details))
        return ok

    def update_action_status(
        self,
        item_id: str,
        status: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> bool:
        return self.update_action(item_id, status=status, owner=owner)

    def bulk_update_status(self, ids: list[str], status: str) -> int:
        n = 0
        for i in ids:
            item = self.resolve_id(i, "action")
            if item and self.update_action(item["id"], status=status):
                n += 1
        return n

    def archive_done(self, *,
                     older_than_days: int = 30,
                     as_of: Optional[date] = None) -> int:
        today = as_of or date.today()
        cutoff = today - timedelta(days=max(older_than_days, 0))
        n = 0
        for a in self.list_actions(status="done"):
            updated = str(a.get("updated_at") or "")[:10]
            try:
                u = date.fromisoformat(updated)
            except ValueError:
                continue
            if u <= cutoff and self.update_action(a["id"], status="archived"):
                n += 1
        return n

    def export_markdown(self) -> str:
        meetings = self.list_meetings()
        lines = ["# Decision Log", ""]

        for m in meetings:
            lines.append(f"## {m['title']}")
            if m.get("meeting_date"):
                lines.append(f"*Meeting date: {m['meeting_date']}*")
            if m.get("summary"):
                lines.append(f"\n{m['summary']}\n")

            decisions = self.list_decisions(meeting_id=m["id"])
            actions = self.list_actions(meeting_id=m["id"], include_closed=True)

            if decisions:
                lines.append("### Decisions")
                for d in decisions:
                    lines.append(f"- **[{d['status']}]** {d['text']}")
                    if d.get("evidence"):
                        lines.append(f"  - _{d['evidence']}_")
                lines.append("")

            if actions:
                lines.append("### Action Items")
                for a in actions:
                    owner = a.get("owner") or "unassigned"
                    due = a.get("due_date") or a.get("due_text") or "—"
                    pri = a.get("priority") or "P2"
                    tag_s = ", ".join(a.get("tags") or []) or "—"
                    lines.append(
                        f"- **[{a['status']}|{pri}]** [{owner}] {a['text']} "
                        f"(due: {due}; tags: {tag_s})"
                    )
                    if a.get("blocked_reason"):
                        lines.append(f"  - blocked: {a['blocked_reason']}")
                    if a.get("evidence"):
                        lines.append(f"  - _{a['evidence']}_")
                    if a.get("notes"):
                        lines.append(f"  - notes: {a['notes']}")
                lines.append("")

            lines.append("---\n")

        return "\n".join(lines).rstrip() + "\n"

    def export_json(self) -> str:
        meetings = self.list_meetings()
        payload = []
        for m in meetings:
            payload.append(
                {
                    "meeting": {
                        "id": m["id"],
                        "title": m["title"],
                        "summary": m.get("summary"),
                        "meeting_date": m.get("meeting_date"),
                        "created_at": m.get("created_at"),
                    },
                    "decisions": self.list_decisions(meeting_id=m["id"]),
                    "action_items": self.list_actions(meeting_id=m["id"], include_closed=True),
                }
            )
        return json.dumps(payload, indent=2, default=str)
