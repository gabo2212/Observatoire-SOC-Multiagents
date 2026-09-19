"""Tool: parse synthetic SOC alert log files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import config


def parse_alert_log(alert_file: str) -> dict[str, Any]:
    """Load and normalize alerts from a synthetic JSON log file.

    Args:
        alert_file: Absolute path, or path relative to data/alerts/
                    (e.g. bruteforce_ssh.json or custom/user_targets.json)
    """
    path = Path(alert_file)
    if not path.is_absolute():
        candidate = config.ALERTS_DIR / alert_file
        path = candidate if candidate.exists() else config.ALERTS_DIR / path.name
    if not path.exists():
        raise FileNotFoundError(f"Alert file not found: {path}")

    alerts = json.loads(path.read_text(encoding="utf-8"))
    severities = {}
    sources = {}
    for a in alerts:
        sev = (a.get("severity") or "unknown").lower()
        severities[sev] = severities.get(sev, 0) + 1
        src = a.get("source") or "unknown"
        sources[src] = sources.get(src, 0) + 1

    return {
        "tool": "parse_alert_log",
        "file": str(path.relative_to(config.ALERTS_DIR) if path.is_relative_to(config.ALERTS_DIR) else path.name),
        "alert_count": len(alerts),
        "severity_breakdown": severities,
        "source_breakdown": sources,
        "alerts": alerts,
        "summary": (
            f"{len(alerts)} alertes chargées depuis {path.name}. "
            f"Gravités: {severities}. Sources: {sources}."
        ),
    }
