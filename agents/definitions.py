"""Thin agent definitions for documentation and imports."""
from __future__ import annotations

import config


def describe_agents() -> list[dict]:
    return [
        {"key": k, **v} for k, v in config.AGENT_ROLES.items()
    ]
