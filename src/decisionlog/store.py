from __future__ import annotations

import json
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
                    title TEXT,
                    summary TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    meeting_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    status TEXT NOT NULL,
                    evidence TEXT,
                    confidence REAL,
                    created_at TEXT,
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
                    FOREIGN KEY (meeting_id) REFERENCES meetings(id)
                );
                """
            )

    def save_extraction(
        self,
        meeting_id: str,
        title: str,
        result: ExtractionResult,
    ) -> None:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO meetings (id, title, summary, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (meeting_id, title, result.meeting_summary, now),
            )

            for d in result.decisions:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO decisions
                    (id, meeting_id, text, status, evidence, confidence, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        d.id,
                        meeting_id,
                        d.text,
                        d.status.value,
                        d.evidence,
                        d.confidence,
                        d.created_at.isoformat(),
                    ),
                )

            for a in result.action_items:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO action_items
                    (id, meeting_id, text, owner, due_date, due_text, status,
                     evidence, confidence, linked_decision_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    ),
                )

    def list_decisions(self, status: Optional[str] = None) -> list[dict]:
        query = "SELECT * FROM decisions"
        params: list = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def list_actions(self, status: Optional[str] = None, owner: Optional[str] = None) -> list[dict]:
        query = "SELECT * FROM action_items"
        clauses = []
        params: list = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if owner:
            clauses.append("owner = ?")
            params.append(owner)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def list_meetings(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM meetings ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]
