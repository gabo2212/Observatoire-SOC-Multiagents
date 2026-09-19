"""Tool: lookup asset inventory for criticality context."""
from __future__ import annotations

from typing import Any

from tools.sites import load_full_inventory


def _load_inventory() -> list[dict[str, Any]]:
    return load_full_inventory()


def lookup_asset_inventory(asset_ids: list[str] | None = None) -> dict[str, Any]:
    """Return inventory rows for given asset IDs (or full inventory)."""
    inventory = _load_inventory()
    if asset_ids:
        wanted = set(asset_ids)
        inventory = [a for a in inventory if a.get("asset_id") in wanted]

    by_id = {a["asset_id"]: a for a in inventory}
    critical = [a for a in inventory if int(a.get("criticality", 0)) >= 4]

    return {
        "tool": "lookup_asset_inventory",
        "asset_count": len(inventory),
        "critical_assets": critical,
        "assets": inventory,
        "by_id": by_id,
        "summary": (
            f"{len(inventory)} actifs résolus; "
            f"{len(critical)} actifs critiques (criticité ≥ 4)."
        ),
    }


def assets_for_alerts(alerts: list[dict[str, Any]]) -> list[str]:
    ids = []
    for a in alerts:
        dst = a.get("dst_asset")
        if dst and dst not in ids:
            ids.append(dst)
    return ids
