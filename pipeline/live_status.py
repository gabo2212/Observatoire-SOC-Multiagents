"""Shared live-run status for UI polling."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

LIVE_PATH = config.TRACES_DIR / "live_status.json"
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_live(payload: dict[str, Any]) -> None:
    LIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = dict(payload)
    data["updated_at"] = _now()
    with _lock:
        LIVE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_live() -> dict[str, Any]:
    if not LIVE_PATH.exists():
        return {"state": "idle"}
    try:
        with _lock:
            return json.loads(LIVE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"state": "idle"}


def clear_live() -> None:
    write_live({"state": "idle", "message": "En attente d'une mission"})
