"""Turn polled live-status snapshots into journal lines.

The API keeps only the latest snapshot. agent_done is overwritten as soon as
the next agent starts, so a line is recorded for every new phase, including
agent_start, instead of waiting for agent_done.
"""
from __future__ import annotations

from typing import Any


def live_note(
    event: dict[str, Any],
    seen: set[tuple],
    seen_output: set[str],
) -> str | None:
    phase = event.get("phase")
    step = event.get("step_index")
    agent = event.get("agent")
    msg = (event.get("message") or "").strip()
    latest = (event.get("latest_output") or "").strip()
    if not msg and not latest:
        return None
    key = (phase, step, agent, msg)
    if key in seen:
        return None
    seen.add(key)
    role = event.get("agent_role") or agent or "Système"
    lines = [f"**{role}** — {msg}" if msg else f"**{role}**"]
    if latest:
        fingerprint = latest[:240]
        if fingerprint not in seen_output:
            seen_output.add(fingerprint)
            lines.append(latest[:800])
    return "\n\n".join(lines)
