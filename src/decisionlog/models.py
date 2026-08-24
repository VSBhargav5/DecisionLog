from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    DECIDED = "decided"
    REVERSED = "reversed"
    SUPERSEDED = "superseded"


class ActionStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ActionPriority(str, Enum):
    P0 = "P0"  # drop everything
    P1 = "P1"  # this week
    P2 = "P2"  # normal
    P3 = "P3"  # backlog


class Decision(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    meeting_id: str
    text: str = Field(..., description="Clear statement of what was decided")
    status: DecisionStatus = DecisionStatus.DECIDED
    evidence: Optional[str] = Field(None, description="Short quote or paraphrase from the source")
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ActionItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    meeting_id: str
    text: str = Field(..., description="What needs to be done")
    owner: Optional[str] = Field(None, description="Person responsible")
    due_date: Optional[date] = None
    due_text: Optional[str] = Field(None, description="Original deadline phrase")
    status: ActionStatus = ActionStatus.OPEN
    priority: ActionPriority = ActionPriority.P2
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    blocked_reason: Optional[str] = None
    evidence: Optional[str] = None
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    linked_decision_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ExtractionResult(BaseModel):
    """Structured result returned by the extractor."""
    decisions: list[Decision] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    meeting_summary: Optional[str] = None
