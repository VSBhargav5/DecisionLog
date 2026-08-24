"""Helpers for personal progress transitions (open → in_progress → done)."""

from __future__ import annotations

from .store import DecisionStore


def start_action(store: DecisionStore, item_id: str) -> bool:
    item = store.resolve_id(item_id, "action")
    if not item:
        return False
    return store.update_action(item["id"], status="in_progress", clear_blocked_reason=True)


def finish_action(store: DecisionStore, item_id: str) -> bool:
    item = store.resolve_id(item_id, "action")
    if not item:
        return False
    return store.update_action(item["id"], status="done", clear_blocked_reason=True)
