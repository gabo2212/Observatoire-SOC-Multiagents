#!/usr/bin/env python3
"""Run a single SOC triage scenario through the observatory API."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from backend.client import ApiError, ObservatoryClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one multi-agent SOC scenario")
    parser.add_argument(
        "--scenario",
        required=True,
        choices=sorted(config.SCENARIOS.keys()),
        help="Scenario key",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip LLM and use deterministic synthesis on tool outputs",
    )
    args = parser.parse_args()

    client = ObservatoryClient()
    try:
        client.health()
        accepted = client.start_run(
            {"scenario": args.scenario, "force_tools_only": args.offline}
        )
        result = client.wait_run(accepted["run_id"])
    except ApiError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
