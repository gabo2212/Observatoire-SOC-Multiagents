#!/usr/bin/env python3
"""Batch-run ≥20 executions across the five SOC scenarios."""
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
from pipeline.llm import llm_ready
from pipeline.tracing import TraceStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-scenario", type=int, default=4, help="Runs per scenario (default 4 → 20)")
    parser.add_argument(
        "--live",
        type=int,
        default=1,
        help="Number of live LLM runs per scenario before switching to offline synthesis",
    )
    parser.add_argument("--offline-only", action="store_true")
    args = parser.parse_args()

    scenarios = list(config.SCENARIOS.keys())
    crew = SOCObservatoryCrew()
    store = crew.store
    results = []

    ready = (not args.offline_only) and llm_ready()
    print(f"LLM ready: {ready}")

    for scenario in scenarios:
        for i in range(args.per_scenario):
            use_offline = args.offline_only or (not ready) or (i >= args.live)
            print(f"→ {scenario} #{i+1} ({'offline' if use_offline else 'live'})")
            try:
                result = crew.run_scenario(scenario, force_tools_only=use_offline)
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR: {exc}")
                result = {"scenario": scenario, "status": "failed", "error": str(exc)}
            results.append(result)
            print(f"  status={result.get('status')} run_id={result.get('run_id')}")

    export_path = store.export_json()
    print(f"Exported {len(store.list_runs())} runs → {export_path}")
    print(json.dumps({"completed": len(results), "results": results}, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
