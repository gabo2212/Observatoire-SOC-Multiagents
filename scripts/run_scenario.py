#!/usr/bin/env python3
"""Run a single SOC triage scenario through the multi-agent crew."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from pipeline.crew_runner import SOCObservatoryCrew


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

    crew = SOCObservatoryCrew()
    result = crew.run_scenario(args.scenario, force_tools_only=args.offline)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
