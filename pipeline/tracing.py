"""SQLite trace store for the multi-agent observatory."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import config


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class StepTrace:
    agent: str
    task: str
    status: str
    model: str
    start_time: str
    end_time: str
    duration_s: float
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    tools_used: list[str] = field(default_factory=list)
    tool_calls: int = 0
    retries: int = 0
    errors: list[str] = field(default_factory=list)
    result_summary: str = ""
    quality_score: float = 0.0
    messages_to: list[str] = field(default_factory=list)
    raw_output: str = ""


class TraceStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path or config.TRACES_DB)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    scenario TEXT NOT NULL,
                    scenario_label TEXT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT NOT NULL,
                    model TEXT,
                    total_duration_s REAL DEFAULT 0,
                    total_tokens_in INTEGER DEFAULT 0,
                    total_tokens_out INTEGER DEFAULT 0,
                    total_cost_usd REAL DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    retry_count INTEGER DEFAULT 0,
                    quality_score REAL DEFAULT 0,
                    final_result TEXT,
                    mission TEXT
                );

                CREATE TABLE IF NOT EXISTS steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    agent TEXT NOT NULL,
                    task TEXT NOT NULL,
                    status TEXT NOT NULL,
                    model TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    duration_s REAL,
                    tokens_in INTEGER,
                    tokens_out INTEGER,
                    cost_usd REAL,
                    tools_used TEXT,
                    tool_calls INTEGER,
                    retries INTEGER,
                    errors TEXT,
                    result_summary TEXT,
                    quality_score REAL,
                    messages_to TEXT,
                    raw_output TEXT,
                    FOREIGN KEY(run_id) REFERENCES runs(run_id)
                );
                """
            )

    def start_run(
        self, scenario: str, mission: str, model: str, scenario_label: str | None = None
    ) -> str:
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"
        label = scenario_label or config.SCENARIOS.get(scenario, {}).get("label", scenario)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO runs (run_id, scenario, scenario_label, started_at, status, model, mission)
                VALUES (?, ?, ?, ?, 'running', ?, ?)
                """,
                (run_id, scenario, label, _utc_now(), model, mission),
            )
        return run_id

    def add_step(self, run_id: str, step_index: int, step: StepTrace) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO steps (
                    run_id, step_index, agent, task, status, model, start_time, end_time,
                    duration_s, tokens_in, tokens_out, cost_usd, tools_used, tool_calls,
                    retries, errors, result_summary, quality_score, messages_to, raw_output
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    step_index,
                    step.agent,
                    step.task,
                    step.status,
                    step.model,
                    step.start_time,
                    step.end_time,
                    step.duration_s,
                    step.tokens_in,
                    step.tokens_out,
                    step.cost_usd,
                    json.dumps(step.tools_used, ensure_ascii=False),
                    step.tool_calls,
                    step.retries,
                    json.dumps(step.errors, ensure_ascii=False),
                    step.result_summary,
                    step.quality_score,
                    json.dumps(step.messages_to, ensure_ascii=False),
                    step.raw_output[:8000],
                ),
            )

    def finish_run(
        self,
        run_id: str,
        *,
        status: str,
        final_result: str,
        quality_score: float,
        totals: dict[str, Any],
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE runs SET
                    ended_at = ?,
                    status = ?,
                    total_duration_s = ?,
                    total_tokens_in = ?,
                    total_tokens_out = ?,
                    total_cost_usd = ?,
                    error_count = ?,
                    retry_count = ?,
                    quality_score = ?,
                    final_result = ?
                WHERE run_id = ?
                """,
                (
                    _utc_now(),
                    status,
                    totals.get("duration_s", 0),
                    totals.get("tokens_in", 0),
                    totals.get("tokens_out", 0),
                    totals.get("cost_usd", 0),
                    totals.get("error_count", 0),
                    totals.get("retry_count", 0),
                    quality_score,
                    final_result,
                    run_id,
                ),
            )

    def list_runs(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY started_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_steps(self, run_id: str) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM steps WHERE run_id = ? ORDER BY step_index",
                (run_id,),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            for key in ("tools_used", "errors", "messages_to"):
                try:
                    d[key] = json.loads(d[key] or "[]")
                except json.JSONDecodeError:
                    d[key] = []
            out.append(d)
        return out

    def export_json(self, path: Path | None = None) -> Path:
        path = Path(path or config.DEMO_TRACES_JSON)
        path.parent.mkdir(parents=True, exist_ok=True)
        runs = self.list_runs()
        payload = []
        for run in runs:
            payload.append({"run": run, "steps": self.get_steps(run["run_id"])})
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def step_to_dict(step: StepTrace) -> dict[str, Any]:
    return asdict(step)
