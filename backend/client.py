"""HTTP client for the observatory API. No Flask import."""
from __future__ import annotations

import time
from typing import Any

import httpx

import config


class ApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload


class ObservatoryClient:
    def __init__(self, base: str | None = None) -> None:
        self.base = (base or config.OBSERVATORY_API_BASE).rstrip("/")

    def health(self) -> dict[str, Any]:
        return self._json("GET", "/api/health")

    def scenarios(self) -> list[dict[str, Any]]:
        payload = self._json("GET", "/api/scenarios")
        return payload if isinstance(payload, list) else []

    def runs(self) -> list[dict[str, Any]]:
        payload = self._json("GET", "/api/runs")
        return list(payload.get("runs") or [])

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self._json("GET", f"/api/runs/{run_id}")

    def start_run(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._json("POST", "/api/runs", json=body, timeout=180.0, ok=(202,))

    def export_runs(self) -> dict[str, Any]:
        return self._json("POST", "/api/runs/export", timeout=120.0)

    def live(self) -> dict[str, Any]:
        return self._json("GET", "/api/live")

    def datasets(self) -> list[dict[str, Any]]:
        payload = self._json("GET", "/api/datasets")
        return payload if isinstance(payload, list) else []

    def import_dataset(
        self,
        *,
        name: str,
        alerts: bytes | None = None,
        assets: bytes | None = None,
        zip_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        files: dict[str, tuple[str, bytes, str]] = {}
        if zip_bytes is not None:
            files["zip"] = ("dataset.zip", zip_bytes, "application/zip")
        if alerts is not None:
            files["alerts"] = ("alerts.json", alerts, "application/json")
        if assets is not None:
            files["assets"] = ("assets.json", assets, "application/json")
        response = self._request(
            "POST",
            "/api/datasets/import",
            data={"name": name},
            files=files,
            timeout=60.0,
        )
        payload = _payload(response)
        if response.status_code in (200, 400) and isinstance(payload, dict):
            return payload
        raise ApiError(
            _error_message(payload, response.status_code),
            status=response.status_code,
            payload=payload if isinstance(payload, dict) else None,
        )

    def inventory(self) -> list[dict[str, Any]]:
        payload = self._json("GET", "/api/inventory")
        return payload if isinstance(payload, list) else []

    def sites(self) -> list[dict[str, Any]]:
        payload = self._json("GET", "/api/sites")
        return payload if isinstance(payload, list) else []

    def add_site(self, **fields: Any) -> dict[str, Any]:
        return self._json("POST", "/api/sites", json=fields, ok=(201,))

    def delete_site(self, asset_id: str) -> None:
        self._json("DELETE", f"/api/sites/{asset_id}")

    def wait_run(self, run_id: str, timeout: float = 3600) -> dict[str, Any]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            live = self.live()
            if live.get("run_id") == run_id and live.get("state") == "failed":
                raise ApiError(str(live.get("error") or live.get("message") or "Mission échouée"))
            run = self.get_run(run_id)
            if run.get("status") not in (None, "running"):
                return run
            time.sleep(0.8)
        raise ApiError("Délai dépassé en attendant la mission")

    def _json(
        self,
        method: str,
        path: str,
        *,
        timeout: float = 30.0,
        ok: tuple[int, ...] = (200,),
        **kwargs: Any,
    ) -> Any:
        response = self._request(method, path, timeout=timeout, **kwargs)
        payload = _payload(response)
        if response.status_code not in ok:
            raise ApiError(
                _error_message(payload, response.status_code),
                status=response.status_code,
                payload=payload if isinstance(payload, dict) else None,
            )
        return payload

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            return httpx.request(method, f"{self.base}{path}", **kwargs)
        except httpx.HTTPError as exc:
            raise ApiError(
                "API injoignable. Démarrez-la avec: python -m backend.app"
            ) from exc


def _payload(response: httpx.Response) -> Any:
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError:
        return {}


def _error_message(payload: Any, status: int) -> str:
    if isinstance(payload, dict) and payload.get("error"):
        return str(payload["error"])
    return f"API {status}"
