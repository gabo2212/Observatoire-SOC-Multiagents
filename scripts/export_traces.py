#!/usr/bin/env python3
"""Export traces DB to JSON."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.tracing import TraceStore


def main() -> None:
    path = TraceStore().export_json()
    print(path)


if __name__ == "__main__":
    main()
