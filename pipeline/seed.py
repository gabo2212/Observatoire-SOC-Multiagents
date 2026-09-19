"""Import exported JSON traces into SQLite when the DB is empty."""
from __future__ import annotations

import json
from pathlib import Path

import config
from pipeline.tracing import TraceStore


def ensure_demo_data(store: TraceStore | None = None) -> int:
    store = store or TraceStore()
    if store.list_runs():
        return 0
    path = Path(config.DEMO_TRACES_JSON)
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    imported = 0
    with store._conn() as conn:
        for item in payload:
            run = item["run"]
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, scenario, scenario_label, started_at, ended_at, status, model,
                    total_duration_s, total_tokens_in, total_tokens_out, total_cost_usd,
                    error_count, retry_count, quality_score, final_result, mission
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run["run_id"],
                    run["scenario"],
                    run.get("scenario_label"),
                    run["started_at"],
                    run.get("ended_at"),
                    run["status"],
                    run.get("model"),
                    run.get("total_duration_s") or 0,
                    run.get("total_tokens_in") or 0,
                    run.get("total_tokens_out") or 0,
                    run.get("total_cost_usd") or 0,
                    run.get("error_count") or 0,
                    run.get("retry_count") or 0,
                    run.get("quality_score") or 0,
                    run.get("final_result"),
                    run.get("mission"),
                ),
            )
            for step in item.get("steps", []):
                tools = step.get("tools_used")
                errors = step.get("errors")
                messages = step.get("messages_to")
                if isinstance(tools, list):
                    tools = json.dumps(tools, ensure_ascii=False)
                if isinstance(errors, list):
                    errors = json.dumps(errors, ensure_ascii=False)
                if isinstance(messages, list):
                    messages = json.dumps(messages, ensure_ascii=False)
                conn.execute(
                    """
                    INSERT INTO steps (
                        run_id, step_index, agent, task, status, model, start_time, end_time,
                        duration_s, tokens_in, tokens_out, cost_usd, tools_used, tool_calls,
                        retries, errors, result_summary, quality_score, messages_to, raw_output
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        step["run_id"],
                        step["step_index"],
                        step["agent"],
                        step["task"],
                        step["status"],
                        step.get("model"),
                        step.get("start_time"),
                        step.get("end_time"),
                        step.get("duration_s"),
                        step.get("tokens_in"),
                        step.get("tokens_out"),
                        step.get("cost_usd"),
                        tools,
                        step.get("tool_calls"),
                        step.get("retries"),
                        errors,
                        step.get("result_summary"),
                        step.get("quality_score"),
                        messages,
                        step.get("raw_output"),
                    ),
                )
            imported += 1
    return imported
