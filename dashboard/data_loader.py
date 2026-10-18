"""Load runs and steps from the observatory API for the Streamlit dashboard."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.client import ObservatoryClient


def fetch_runs() -> list[dict[str, Any]]:
    return ObservatoryClient().runs()


def runs_df(rows: list[dict[str, Any]] | None = None) -> pd.DataFrame:
    rows = fetch_runs() if rows is None else rows
    slim = [{key: value for key, value in row.items() if key != "steps"} for row in rows]
    if not slim:
        return pd.DataFrame()
    return pd.DataFrame(slim)


def steps_df(rows: list[dict[str, Any]] | None = None) -> pd.DataFrame:
    rows = fetch_runs() if rows is None else rows
    frames = []
    for run in rows:
        for step in run.get("steps") or []:
            step = dict(step)
            step["scenario"] = run.get("scenario")
            step["scenario_label"] = run.get("scenario_label")
            step["run_status"] = run.get("status")
            frames.append(step)
    if not frames:
        return pd.DataFrame()
    return pd.DataFrame(frames)


def filter_runs(
    df: pd.DataFrame,
    *,
    scenarios: list[str] | None = None,
    statuses: list[str] | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if scenarios:
        out = out[out["scenario"].isin(scenarios)]
    if statuses:
        out = out[out["status"].isin(statuses)]
    return out


def kpi_dict(runs: pd.DataFrame, steps: pd.DataFrame) -> dict[str, Any]:
    if runs.empty:
        return {
            "n_runs": 0,
            "success_rate": 0.0,
            "avg_duration": 0.0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "errors": 0,
            "most_used_agent": "—",
            "slowest_agent": "—",
        }
    success = (runs["status"] == "success").sum()
    most_used = "—"
    slowest = "—"
    if not steps.empty:
        most_used = steps["agent"].value_counts().idxmax()
        slowest = steps.groupby("agent")["duration_s"].mean().idxmax()
    return {
        "n_runs": int(len(runs)),
        "success_rate": round(100.0 * success / len(runs), 1),
        "avg_duration": round(float(runs["total_duration_s"].mean()), 2),
        "total_tokens": int(runs["total_tokens_in"].sum() + runs["total_tokens_out"].sum()),
        "total_cost": round(float(runs["total_cost_usd"].sum()), 4),
        "errors": int(runs["error_count"].sum()),
        "most_used_agent": most_used,
        "slowest_agent": slowest,
    }


def parse_list_field(val: Any) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except json.JSONDecodeError:
            return []
    return []
