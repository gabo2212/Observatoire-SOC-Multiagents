"""Dataset registry, schema validation, and import for SOC triage."""
from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import config
from tools.sites import load_full_inventory, load_lab_inventory

DATASETS_DIR = config.DATA_DIR / "datasets"
IMPORTS_DIR = DATASETS_DIR / "_imports"

SCHEMA_VERSION = 1
REQUIRED_ALERT_FIELDS = ("alert_id", "ts", "source", "rule", "severity", "dst_asset", "msg")
ALLOWED_SEVERITIES = {"critical", "high", "medium", "low", "info", "unknown"}
REQUIRED_ASSET_FIELDS = ("asset_id", "hostname", "type", "criticality")


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    alert_count: int = 0
    asset_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings,
            "alert_count": self.alert_count,
            "asset_count": self.asset_count,
        }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_dataset_payload(
    alerts: list[dict[str, Any]],
    assets: list[dict[str, Any]] | None = None,
    *,
    merge_lab_inventory: bool = True,
) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(alerts, list) or not alerts:
        return ValidationResult(False, ["alerts must be a non-empty JSON list"])

    asset_rows = list(assets or [])
    if merge_lab_inventory:
        by_id = {a["asset_id"]: a for a in load_lab_inventory()}
        for a in asset_rows:
            by_id[a["asset_id"]] = a
        # also include user sites so custom targets resolve
        for a in load_full_inventory():
            by_id.setdefault(a["asset_id"], a)
        asset_map = by_id
    else:
        asset_map = {a["asset_id"]: a for a in asset_rows}

    for i, asset in enumerate(asset_rows):
        if not isinstance(asset, dict):
            errors.append(f"assets[{i}] must be an object")
            continue
        for f in REQUIRED_ASSET_FIELDS:
            if f not in asset:
                errors.append(f"assets[{i}] missing field '{f}'")
        try:
            c = int(asset.get("criticality", 0))
            if c < 1 or c > 5:
                errors.append(f"assets[{i}].criticality must be 1..5")
        except (TypeError, ValueError):
            errors.append(f"assets[{i}].criticality must be an int")

    seen_ids: set[str] = set()
    for i, alert in enumerate(alerts):
        if not isinstance(alert, dict):
            errors.append(f"alerts[{i}] must be an object")
            continue
        for f in REQUIRED_ALERT_FIELDS:
            if f not in alert or alert[f] in (None, ""):
                errors.append(f"alerts[{i}] missing required field '{f}'")
        sev = str(alert.get("severity", "")).lower()
        if sev and sev not in ALLOWED_SEVERITIES:
            errors.append(
                f"alerts[{i}].severity '{sev}' invalid; use {sorted(ALLOWED_SEVERITIES)}"
            )
        aid = alert.get("alert_id")
        if aid in seen_ids:
            errors.append(f"duplicate alert_id '{aid}'")
        seen_ids.add(aid)
        dst = alert.get("dst_asset")
        if dst and dst not in asset_map:
            errors.append(
                f"alerts[{i}].dst_asset '{dst}' not found in inventory "
                "(add it to assets.json or use a known lab asset_id)"
            )
        if "src_ip" not in alert:
            warnings.append(f"alerts[{i}] has no src_ip (optional but useful for correlation)")

    ok = not errors
    return ValidationResult(
        ok=ok,
        errors=errors,
        warnings=warnings,
        alert_count=len(alerts),
        asset_count=len(asset_map),
    )


def list_datasets() -> list[dict[str, Any]]:
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    roots = [DATASETS_DIR, IMPORTS_DIR]
    for base in roots:
        for path in sorted(base.iterdir()):
            if not path.is_dir() or path.name.startswith("_"):
                continue
            manifest_path = path / "manifest.json"
            alerts_path = path / "alerts.json"
            if not manifest_path.exists() or not alerts_path.exists():
                continue
            manifest = _read_json(manifest_path)
            assets_path = path / "assets.json"
            assets = _read_json(assets_path) if assets_path.exists() else None
            alerts = _read_json(alerts_path)
            validation = validate_dataset_payload(alerts, assets)
            out.append(
                {
                    **manifest,
                    "id": manifest.get("id") or path.name,
                    "path": str(path),
                    "compatible": validation.ok,
                    "validation": validation.as_dict(),
                    "has_custom_assets": assets_path.exists(),
                    "imported": base == IMPORTS_DIR,
                }
            )
    return out


def get_dataset(dataset_id: str) -> dict[str, Any]:
    path = DATASETS_DIR / dataset_id
    if not path.exists():
        # imported ids
        path = IMPORTS_DIR / dataset_id
    if not (path / "manifest.json").exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_id}")
    manifest = _read_json(path / "manifest.json")
    alerts = _read_json(path / "alerts.json")
    assets = _read_json(path / "assets.json") if (path / "assets.json").exists() else None
    validation = validate_dataset_payload(alerts, assets)
    return {
        "id": dataset_id,
        "manifest": manifest,
        "alerts": alerts,
        "assets": assets,
        "alerts_path": path / "alerts.json",
        "assets_path": (path / "assets.json") if assets is not None else None,
        "validation": validation,
        "compatible": validation.ok,
    }


def ensure_runtime_files(dataset_id: str) -> dict[str, Any]:
    """Copy dataset alerts (and optional assets overlay note) into runnable paths."""
    ds = get_dataset(dataset_id)
    if not ds["compatible"]:
        raise ValueError(
            "Dataset incompatible: " + "; ".join(ds["validation"].errors[:5])
        )

    # Materialize alerts under data/alerts/datasets/<id>.json for the parser
    dest_dir = config.ALERTS_DIR / "datasets"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{dataset_id}.json"
    shutil.copyfile(ds["alerts_path"], dest)

    # If dataset ships assets, merge into a runtime overlay used by inventory lookup
    overlay_path = config.DATA_DIR / "inventory" / "dataset_overlay.json"
    if ds["assets"]:
        overlay_path.write_text(
            json.dumps(ds["assets"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    elif overlay_path.exists():
        overlay_path.write_text("[]\n", encoding="utf-8")

    return {
        "alert_file": str(dest),
        "mission": ds["manifest"].get("mission"),
        "label": ds["manifest"].get("name"),
        "dataset_id": dataset_id,
        "validation": ds["validation"].as_dict(),
    }


def import_alerts_json(
    raw: bytes | str,
    *,
    name: str,
    mission: str | None = None,
    assets_raw: bytes | str | None = None,
) -> dict[str, Any]:
    """Import a standalone alerts JSON (and optional assets) as a new dataset."""
    alerts = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
    assets = None
    if assets_raw:
        assets = json.loads(
            assets_raw if isinstance(assets_raw, str) else assets_raw.decode("utf-8")
        )

    validation = validate_dataset_payload(alerts, assets)
    if not validation.ok:
        return {"ok": False, "validation": validation.as_dict()}

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "import"
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMPORTS_DIR / slug
    # unique
    n = 2
    base = slug
    while dest.exists():
        slug = f"{base}-{n}"
        dest = IMPORTS_DIR / slug
        n += 1

    dest.mkdir(parents=True)
    manifest = {
        "id": slug,
        "name": name,
        "description": "Dataset importé via l'UI",
        "version": "1.0",
        "schema_version": SCHEMA_VERSION,
        "mission": mission
        or f"Trier et prioriser les alertes du jeu de données importé « {name} ».",
        "tags": ["imported"],
        "source": "upload",
    }
    (dest / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (dest / "alerts.json").write_text(
        json.dumps(alerts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if assets:
        (dest / "assets.json").write_text(
            json.dumps(assets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return {"ok": True, "dataset_id": slug, "validation": validation.as_dict(), "manifest": manifest}


def import_dataset_zip(raw: bytes, *, fallback_name: str = "import-zip") -> dict[str, Any]:
    """Import a zip containing manifest.json + alerts.json (+ optional assets.json)."""
    IMPORTS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = IMPORTS_DIR / "_tmp_upload.zip"
    tmp.write_bytes(raw)
    extract_to = IMPORTS_DIR / "_tmp_extract"
    if extract_to.exists():
        shutil.rmtree(extract_to)
    extract_to.mkdir()
    with zipfile.ZipFile(tmp, "r") as zf:
        zf.extractall(extract_to)

    # find folder that contains alerts.json
    root = extract_to
    candidates = [p for p in extract_to.rglob("alerts.json")]
    if not candidates:
        return {"ok": False, "validation": {"ok": False, "errors": ["zip missing alerts.json"]}}
    root = candidates[0].parent
    alerts = _read_json(root / "alerts.json")
    assets = _read_json(root / "assets.json") if (root / "assets.json").exists() else None
    manifest = (
        _read_json(root / "manifest.json")
        if (root / "manifest.json").exists()
        else {
            "id": fallback_name,
            "name": fallback_name,
            "mission": f"Trier le dataset {fallback_name}",
            "schema_version": SCHEMA_VERSION,
            "tags": ["imported", "zip"],
        }
    )
    validation = validate_dataset_payload(alerts, assets)
    if not validation.ok:
        return {"ok": False, "validation": validation.as_dict()}

    slug = re.sub(r"[^a-z0-9]+", "-", str(manifest.get("id") or fallback_name).lower()).strip("-")
    dest = IMPORTS_DIR / slug
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(root, dest)
    (dest / "manifest.json").write_text(
        json.dumps({**manifest, "id": slug, "source": "zip"}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    shutil.rmtree(extract_to, ignore_errors=True)
    tmp.unlink(missing_ok=True)
    return {"ok": True, "dataset_id": slug, "validation": validation.as_dict(), "manifest": manifest}


def schema_example() -> dict[str, Any]:
    return {
        "alerts.json": [
            {
                "alert_id": "ALT-EX-001",
                "ts": "2026-09-18T10:00:00Z",
                "source": "ids",
                "rule": "EXAMPLE_RULE",
                "severity": "high",
                "src_ip": "203.0.113.10",
                "dst_asset": "SRV-WEB01",
                "user": None,
                "msg": "Example synthetic alert",
            }
        ],
        "assets.json_optional": [
            {
                "asset_id": "SRV-WEB01",
                "hostname": "web.example.local",
                "type": "web_server",
                "criticality": 4,
                "owner": "DevOps",
                "zone": "dmz",
            }
        ],
        "severities": sorted(ALLOWED_SEVERITIES),
        "notes": (
            "dst_asset must exist in assets.json OR in the default ACME-LAB inventory "
            "(SRV-DC01, SRV-WEB01, …). schema_version=1."
        ),
    }
