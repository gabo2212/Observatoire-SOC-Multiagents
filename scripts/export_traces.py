#!/usr/bin/env python3
"""Export traces DB to JSON through the observatory API."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.client import ApiError, ObservatoryClient


def main() -> None:
    try:
        exported = ObservatoryClient().export_runs()
    except ApiError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(exported["path"])


if __name__ == "__main__":
    main()
