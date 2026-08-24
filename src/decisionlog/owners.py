"""Normalize person names so 'Sarah K.' and 'sarah' count as one owner."""

from __future__ import annotations

import re
from typing import Optional


def normalize_owner(name: Optional[str], aliases: dict[str, str] | None = None) -> Optional[str]:
    if name is None:
        return None
    raw = name.strip()
    if not raw:
        return None
    key = re.sub(r"\s+", " ", raw).strip().lower()
    key = key.rstrip(".")
    if aliases:
        # exact then first-token match
        if key in aliases:
            return aliases[key]
        first = key.split()[0]
        if first in aliases:
            return aliases[first]
    # Title-case multi-word; keep simple capitalization
    return " ".join(p.capitalize() for p in key.split())


def load_alias_map(raw: dict | None) -> dict[str, str]:
    """Map alias keys (lower) → canonical display name."""
    out: dict[str, str] = {}
    if not raw:
        return out
    for alias, canonical in raw.items():
        if not alias or not canonical:
            continue
        out[str(alias).strip().lower()] = str(canonical).strip()
    return out
