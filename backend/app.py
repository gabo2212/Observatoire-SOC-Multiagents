"""Flask API. The only process that writes traces, sites, datasets, and live status."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from flask import Flask, jsonify, request

from backend.jobs import JobRunner, MissionBusy
from pipeline.datasets import import_alerts_json, import_dataset_zip, list_datasets
from pipeline.live_status import clear_live, read_live
from pipeline.llm import llm_ready
from pipeline.tracing import TraceStore
from tools.sites import add_user_site, delete_user_site, load_full_inventory, load_user_sites


def _runs_payload(store: TraceStore) -> list[dict]:
    payload = []
    for run in store.list_runs():
        payload.append({**run, "steps": store.get_steps(run["run_id"])})
    return payload


def create_app() -> Flask:
    app = Flask(__name__)
    store = TraceStore()
    store.seed_if_empty()
    jobs = JobRunner(store)
    clear_live()

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "llm_ready": llm_ready()})

    @app.get("/api/scenarios")
    def scenarios():
        return jsonify(
            [
                {"key": key, "label": meta["label"], "mission": meta["mission"]}
                for key, meta in config.SCENARIOS.items()
            ]
        )

    @app.get("/api/runs")
    def list_runs():
        return jsonify({"runs": _runs_payload(store)})

    @app.post("/api/runs/export")
    def export_runs():
        path = store.export_json()
        return jsonify({"path": str(path), "count": len(store.list_runs())})

    @app.get("/api/runs/<run_id>")
    def get_run(run_id: str):
        run = store.get_run(run_id)
        if not run:
            return jsonify({"error": "Exécution introuvable"}), 404
        return jsonify({**run, "steps": store.get_steps(run_id)})

    @app.post("/api/runs")
    def start_run():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Corps JSON attendu"}), 400
        try:
            run_id = jobs.start(body)
        except MissionBusy as exc:
            return jsonify({"error": str(exc)}), 409
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except (RuntimeError, TimeoutError) as exc:
            return jsonify({"error": str(exc)}), 500
        stored = store.get_run(run_id)
        status = stored["status"] if stored else "running"
        return jsonify({"run_id": run_id, "status": status}), 202

    @app.get("/api/live")
    def live():
        return jsonify(read_live())

    @app.get("/api/datasets")
    def datasets():
        return jsonify(list_datasets())

    @app.post("/api/datasets/import")
    def import_dataset():
        name = (request.form.get("name") or "Mon import").strip() or "Mon import"
        uploaded_zip = request.files.get("zip")
        alerts = request.files.get("alerts")
        assets = request.files.get("assets")
        if uploaded_zip is not None and uploaded_zip.filename:
            result = import_dataset_zip(uploaded_zip.read(), fallback_name=name)
        elif alerts is not None and alerts.filename:
            assets_raw = assets.read() if assets is not None and assets.filename else None
            result = import_alerts_json(alerts.read(), name=name, assets_raw=assets_raw)
        else:
            result = {
                "ok": False,
                "validation": {"errors": ["Ajoutez un JSON ou un ZIP."]},
            }
        return jsonify(result), (200 if result.get("ok") else 400)

    @app.get("/api/inventory")
    def inventory():
        return jsonify(load_full_inventory())

    @app.get("/api/sites")
    def sites():
        return jsonify(load_user_sites())

    @app.post("/api/sites")
    def create_site():
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Corps JSON attendu"}), 400
        try:
            row = add_user_site(
                hostname=str(body.get("hostname") or ""),
                name=body.get("name") or None,
                site_type=str(body.get("site_type") or "web_server"),
                criticality=int(body.get("criticality") or 4),
                owner=str(body.get("owner") or "Moi"),
                zone=str(body.get("zone") or "dmz"),
                url=str(body.get("url") or ""),
            )
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(row), 201

    @app.delete("/api/sites/<asset_id>")
    def remove_site(asset_id: str):
        if not delete_user_site(asset_id):
            return jsonify({"error": "Cible introuvable"}), 404
        return jsonify({"deleted": True})

    return app


app = create_app()


def main() -> None:
    app.run(
        host="127.0.0.1",
        port=config.API_PORT,
        threaded=True,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
