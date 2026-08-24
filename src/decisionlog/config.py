"""Optional ~/.decisionlog/config.json for aliases and defaults."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_DIR = Path.home() / ".decisionlog"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG_PATH
    if not cfg_path.exists():
        return {}
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save_config(data: dict[str, Any], path: Path | None = None) -> Path:
    cfg_path = path or DEFAULT_CONFIG_PATH
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return cfg_path


def owner_aliases(config: dict[str, Any] | None = None) -> dict[str, str]:
    cfg = config if config is not None else load_config()
    raw = cfg.get("owner_aliases") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(k).lower(): str(v) for k, v in raw.items() if k and v}
