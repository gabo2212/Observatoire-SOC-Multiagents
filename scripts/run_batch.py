#!/usr/bin/env python3
"""Batch-run executions across the five SOC scenarios, via the API."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.client import ApiError, ObservatoryClient


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

    client = ObservatoryClient()
    try:
        health = client.health()
        scenarios = [row["key"] for row in client.scenarios()]
    except ApiError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    results = []
    ready = (not args.offline_only) and bool(health.get("llm_ready"))
    print(f"LLM ready: {ready}")

    for scenario in scenarios:
        for i in range(args.per_scenario):
            use_offline = args.offline_only or (not ready) or (i >= args.live)
            print(f"→ {scenario} #{i + 1} ({'offline' if use_offline else 'live'})")
            try:
                accepted = client.start_run(
                    {"scenario": scenario, "force_tools_only": use_offline}
                )
                result = client.wait_run(accepted["run_id"])
            except ApiError as exc:
                print(f"  ERROR: {exc}")
                result = {"scenario": scenario, "status": "failed", "error": str(exc)}
            results.append(result)
            print(f"  status={result.get('status')} run_id={result.get('run_id')}")

    try:
        exported = client.export_runs()
    except ApiError as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Exported {exported['count']} runs → {exported['path']}")
    print(json.dumps({"completed": len(results), "results": results}, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    main()
