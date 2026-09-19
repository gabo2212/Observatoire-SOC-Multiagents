"""User-defined sites / assets (your targets in the observatory)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import config

USER_SITES_PATH = config.DATA_DIR / "inventory" / "user_sites.json"
CUSTOM_ALERTS_DIR = config.DATA_DIR / "alerts" / "custom"


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).strip("-").upper()
    return (s or "SITE")[:24]


def load_lab_inventory() -> list[dict[str, Any]]:
    return json.loads(config.INVENTORY_PATH.read_text(encoding="utf-8"))


def load_user_sites() -> list[dict[str, Any]]:
    if not USER_SITES_PATH.exists():
        return []
    return json.loads(USER_SITES_PATH.read_text(encoding="utf-8"))


def save_user_sites(sites: list[dict[str, Any]]) -> None:
    USER_SITES_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_SITES_PATH.write_text(
        json.dumps(sites, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_full_inventory() -> list[dict[str, Any]]:
    """Lab demo assets + dataset overlay + your sites."""
    by_id: dict[str, dict[str, Any]] = {}
    for row in load_lab_inventory():
        by_id[row["asset_id"]] = row
    overlay = config.DATA_DIR / "inventory" / "dataset_overlay.json"
    if overlay.exists():
        try:
            for row in json.loads(overlay.read_text(encoding="utf-8")):
                by_id[row["asset_id"]] = row
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    for row in load_user_sites():
        by_id[row["asset_id"]] = row
    return list(by_id.values())


def add_user_site(
    *,
    hostname: str,
    name: str | None = None,
    site_type: str = "web_server",
    criticality: int = 4,
    owner: str = "Moi",
    zone: str = "dmz",
    url: str = "",
) -> dict[str, Any]:
    hostname = hostname.strip().lower().removeprefix("https://").removeprefix("http://")
    hostname = hostname.split("/")[0]
    if not hostname:
        raise ValueError("Hostname / domaine requis")

    sites = load_user_sites()
    asset_id = f"USER-{_slug(name or hostname)}"
    # ensure unique
    existing_ids = {s["asset_id"] for s in sites}
    base = asset_id
    n = 2
    while asset_id in existing_ids:
        asset_id = f"{base}-{n}"
        n += 1

    row = {
        "asset_id": asset_id,
        "hostname": hostname,
        "name": name or hostname,
        "type": site_type,
        "criticality": int(criticality),
        "owner": owner,
        "zone": zone,
        "url": url or f"https://{hostname}",
        "source": "user",
    }
    sites.append(row)
    save_user_sites(sites)
    return row


def delete_user_site(asset_id: str) -> bool:
    sites = load_user_sites()
    new = [s for s in sites if s["asset_id"] != asset_id]
    if len(new) == len(sites):
        return False
    save_user_sites(new)
    return True


def build_alerts_for_targets(
    target_ids: list[str],
    *,
    pattern: str = "web_probe",
) -> tuple[Path, list[dict[str, Any]]]:
    """Create a synthetic alert file aimed at the selected user/lab assets."""
    inventory = {a["asset_id"]: a for a in load_full_inventory()}
    targets = [inventory[i] for i in target_ids if i in inventory]
    if not targets:
        raise ValueError("Aucun actif cible valide")

    alerts: list[dict[str, Any]] = []
    for i, asset in enumerate(targets, start=1):
        host = asset.get("hostname") or asset["asset_id"]
        if pattern == "bruteforce":
            alerts.extend(
                [
                    {
                        "alert_id": f"ALT-U-{i:02d}A",
                        "ts": "2026-09-19T03:10:00Z",
                        "source": "ids",
                        "rule": "SSH_BRUTE_FORCE",
                        "severity": "high",
                        "src_ip": "203.0.113.88",
                        "dst_asset": asset["asset_id"],
                        "user": None,
                        "msg": f"Brute-force détecté vers {host}",
                    },
                    {
                        "alert_id": f"ALT-U-{i:02d}B",
                        "ts": "2026-09-19T03:12:00Z",
                        "source": "auth",
                        "rule": "SUCCESS_AFTER_FAILURES",
                        "severity": "critical",
                        "src_ip": "203.0.113.88",
                        "dst_asset": asset["asset_id"],
                        "user": "admin",
                        "msg": f"Connexion réussie après échecs sur {host}",
                    },
                ]
            )
        elif pattern == "exfil":
            alerts.append(
                {
                    "alert_id": f"ALT-U-{i:02d}",
                    "ts": "2026-09-19T01:20:00Z",
                    "source": "dlp",
                    "rule": "LARGE_UPLOAD",
                    "severity": "high",
                    "src_ip": "10.9.9.9",
                    "dst_asset": asset["asset_id"],
                    "user": "operator",
                    "msg": f"Upload volumineux suspect depuis/vers {host}",
                }
            )
        else:  # web_probe / noisy
            alerts.extend(
                [
                    {
                        "alert_id": f"ALT-U-{i:02d}A",
                        "ts": "2026-09-19T11:00:00Z",
                        "source": "waf",
                        "rule": "BOT_SCAN",
                        "severity": "medium",
                        "src_ip": "198.51.100.40",
                        "dst_asset": asset["asset_id"],
                        "user": None,
                        "msg": f"Scan automatisé contre {host} ({asset.get('url', '')})",
                    },
                    {
                        "alert_id": f"ALT-U-{i:02d}B",
                        "ts": "2026-09-19T11:02:00Z",
                        "source": "ids",
                        "rule": "SQLI_GENERIC",
                        "severity": "medium",
                        "src_ip": "198.51.100.41",
                        "dst_asset": asset["asset_id"],
                        "user": None,
                        "msg": f"Sondes SQLi génériques sur {host}",
                    },
                    {
                        "alert_id": f"ALT-U-{i:02d}C",
                        "ts": "2026-09-19T11:05:00Z",
                        "source": "edr",
                        "rule": "WEB_SHELL_WRITE",
                        "severity": "critical",
                        "src_ip": "10.0.0.5",
                        "dst_asset": asset["asset_id"],
                        "user": "www-data",
                        "msg": f"Écriture fichier suspecte sur {host} — à prioriser",
                    },
                ]
            )

    CUSTOM_ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    path = CUSTOM_ALERTS_DIR / "user_targets.json"
    path.write_text(json.dumps(alerts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path, alerts
