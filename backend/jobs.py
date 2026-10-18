"""One mission at a time, run inside the API process."""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any

import config
from pipeline.crew_runner import SOCObservatoryCrew
from pipeline.datasets import ensure_runtime_files
from pipeline.live_status import read_live, write_live
from pipeline.tracing import TraceStore
from tools.sites import build_alerts_for_targets, load_full_inventory


class MissionBusy(Exception):
    """Another triage mission is already running in this process."""


def prepare_mission(body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Turn a POST /api/runs body into crew.run_scenario arguments."""
    force = bool(body.get("force_tools_only"))
    kwargs: dict[str, Any] = {"force_tools_only": force}
    dataset_id = body.get("dataset_id")
    targets = body.get("targets") or []
    scenario = body.get("scenario")

    if dataset_id:
        try:
            prepared = ensure_runtime_files(str(dataset_id))
        except FileNotFoundError as exc:
            raise ValueError(str(exc)) from exc
        kwargs.update(
            alert_file=prepared["alert_file"],
            label_override=prepared["label"],
            mission_override=prepared["mission"],
        )
        return f"dataset_{dataset_id}", kwargs

    if targets:
        if not isinstance(targets, list):
            raise ValueError("targets doit être une liste")
        pattern = str(body.get("pattern") or "web_probe")
        alert_path, _alerts = build_alerts_for_targets(
            [str(item) for item in targets], pattern=pattern
        )
        wanted = set(targets)
        hosts = [
            asset.get("hostname")
            for asset in load_full_inventory()
            if asset["asset_id"] in wanted and asset.get("hostname")
        ]
        kwargs.update(
            alert_file=str(alert_path),
            label_override="Mission cibles personnelles",
            mission_override=(
                "Trier et prioriser les alertes synthétiques visant: "
                + ", ".join(hosts)
                + ". Produire un brief P1/P2/P3 pour ces actifs."
            ),
        )
        return "user_custom", kwargs

    if not scenario or str(scenario) not in config.SCENARIOS:
        raise ValueError("Choisissez un scénario, un dataset ou des cibles.")
    return str(scenario), kwargs


class JobRunner:
    def __init__(self, store: TraceStore) -> None:
        self.store = store
        self._lock = threading.Lock()
        self._running = False
        self._job_id: str | None = None

    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    def start(self, body: dict[str, Any]) -> str:
        job_id = uuid.uuid4().hex
        with self._lock:
            if self._running:
                raise MissionBusy("Une mission est déjà en cours")
            self._running = True
            self._job_id = job_id

        try:
            scenario, kwargs = prepare_mission(body)
        except Exception:
            self._finish(job_id)
            raise

        holder: dict[str, Any] = {}

        def work() -> None:
            try:
                crew = SOCObservatoryCrew(store=self.store)
                holder["result"] = crew.run_scenario(scenario, **kwargs)
            except Exception as exc:  # noqa: BLE001
                holder["error"] = str(exc)
                previous = read_live()
                run_id = previous.get("run_id")
                if run_id:
                    current = self.store.get_run(str(run_id))
                    if current and current.get("status") == "running":
                        self.store.finish_run(
                            str(run_id),
                            status="failed",
                            final_result=str(exc),
                            quality_score=0.0,
                            totals={},
                        )
                write_live(
                    {
                        "state": "failed",
                        "run_id": run_id,
                        "message": str(exc),
                        "error": str(exc),
                        "progress": previous.get("progress") or 0,
                    }
                )
            finally:
                self._finish(job_id)

        write_live({"state": "starting", "message": "Démarrage de la mission"})
        threading.Thread(target=work, name=f"mission-{job_id[:8]}", daemon=True).start()
        return self._wait_for_run_id(holder)

    def _finish(self, job_id: str) -> None:
        with self._lock:
            if self._job_id == job_id:
                self._running = False

    def _wait_for_run_id(self, holder: dict[str, Any]) -> str:
        deadline = time.time() + 120
        while time.time() < deadline:
            result = holder.get("result")
            if result and result.get("run_id"):
                return str(result["run_id"])
            live = read_live()
            if live.get("run_id") and live.get("state") in ("running", "done", "failed"):
                return str(live["run_id"])
            if holder.get("error") and not live.get("run_id"):
                raise RuntimeError(holder["error"])
            time.sleep(0.05)
        if holder.get("error"):
            raise RuntimeError(holder["error"])
        raise TimeoutError("La mission n'a pas démarré")
