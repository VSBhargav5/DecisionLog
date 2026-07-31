from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .models import ActionItem, ActionStatus, Decision, DecisionStatus, ExtractionResult


DEFAULT_DB = Path.home() / ".decisionlog" / "decisions.db"


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
                    evidence TEXT,
                    confidence REAL,
                    linked_decision_id TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
                );

                CREATE INDEX IF NOT EXISTS idx_meetings_title ON meetings(title);
                CREATE INDEX IF NOT EXISTS idx_actions_status ON action_items(status);
                CREATE INDEX IF NOT EXISTS idx_actions_owner ON action_items(owner);
                """
            )

    # ── Meetings ──────────────────────────────────────────────

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

    # ── Save / Re-run ─────────────────────────────────────────

    def save_extraction(
        self,
        meeting_id: str,
        title: str,
        result: ExtractionResult,
        *,
        meeting_date: Optional[date] = None,
        replace_existing: bool = False,
    ) -> str:
        """
        Persist an extraction result.

        If replace_existing=True and a meeting with the same title already exists,
        its previous decisions/actions are removed and replaced (true re-run).
        Returns the meeting_id that was used.
        """
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
                    SET summary = ?, meeting_date = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        result.meeting_summary,
                        meeting_date.isoformat() if meeting_date else existing.get("meeting_date"),
                        now,
                        meeting_id,
                    ),
                )
        else:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO meetings
                    (id, title, summary, meeting_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        meeting_id,
                        title,
                        result.meeting_summary,
                        meeting_date.isoformat() if meeting_date else None,
                        now,
                        now,
                    ),
                )

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
                conn.execute(
                    """
                    INSERT OR REPLACE INTO action_items
                    (id, meeting_id, text, owner, due_date, due_text, status,
                     evidence, confidence, linked_decision_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        a.id,
                        meeting_id,
                        a.text,
                        a.owner,
                        a.due_date.isoformat() if a.due_date else None,
                        a.due_text,
                        a.status.value,
                        a.evidence,
                        a.confidence,
                        a.linked_decision_id,
                        a.created_at.isoformat(),
                        a.updated_at.isoformat(),
                    ),
                )

        return meeting_id

    # ── Read ──────────────────────────────────────────────────

    def list_decisions(self, status: Optional[str] = None) -> list[dict]:
        query = "SELECT d.*, m.title AS meeting_title FROM decisions d JOIN meetings m ON d.meeting_id = m.id"
        params: list = []
        if status:
            query += " WHERE d.status = ?"
            params.append(status)
        query += " ORDER BY d.created_at DESC"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def list_actions(
        self,
        status: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> list[dict]:
        query = "SELECT a.*, m.title AS meeting_title FROM action_items a JOIN meetings m ON a.meeting_id = m.id"
        clauses = []
        params: list = []
        if status:
            clauses.append("a.status = ?")
            params.append(status)
        if owner:
            clauses.append("a.owner = ?")
            params.append(owner)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY a.created_at DESC"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(query, params).fetchall()]

    def list_meetings(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM meetings ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_decision(self, item_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM decisions WHERE id = ?", (item_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_action(self, item_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM action_items WHERE id = ?", (item_id,)
            ).fetchone()
            return dict(row) if row else None

    # ── Status updates ────────────────────────────────────────

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
            return cur.rowcount > 0

    def update_action_status(
        self,
        item_id: str,
        status: Optional[str] = None,
        owner: Optional[str] = None,
    ) -> bool:
        if status:
            try:
                ActionStatus(status)
            except ValueError:
                return False

        sets = []
        params: list = []
        if status:
            sets.append("status = ?")
            params.append(status)
        if owner is not None:
            sets.append("owner = ?")
            params.append(owner if owner else None)

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
            return cur.rowcount > 0

    # ── Export helpers ────────────────────────────────────────

    def export_markdown(self) -> str:
        meetings = self.list_meetings()
        lines = ["# Decision Log", ""]

        for m in meetings:
            lines.append(f"## {m['title']}")
            if m.get("meeting_date"):
                lines.append(f"*Meeting date: {m['meeting_date']}*")
            if m.get("summary"):
                lines.append(f"\n{m['summary']}\n")

            decisions = [
                d for d in self.list_decisions() if d["meeting_id"] == m["id"]
            ]
            actions = [
                a for a in self.list_actions() if a["meeting_id"] == m["id"]
            ]

            if decisions:
                lines.append("### Decisions")
                for d in decisions:
                    status = d["status"]
                    lines.append(f"- **[{status}]** {d['text']}")
                    if d.get("evidence"):
                        lines.append(f"  - _{d['evidence']}_")
                lines.append("")

            if actions:
                lines.append("### Action Items")
                for a in actions:
                    owner = a.get("owner") or "unassigned"
                    due = a.get("due_date") or a.get("due_text") or "—"
                    status = a["status"]
                    lines.append(f"- **[{status}]** [{owner}] {a['text']} (due: {due})")
                    if a.get("evidence"):
                        lines.append(f"  - _{a['evidence']}_")
                lines.append("")

            lines.append("---\n")

        return "\n".join(lines).rstrip() + "\n"
