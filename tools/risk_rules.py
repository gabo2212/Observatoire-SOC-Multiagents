"""Tool: deterministic risk scoring for SOC triage verification."""
from __future__ import annotations

from typing import Any

SEVERITY_WEIGHT = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "info": 1,
    "unknown": 2,
}


def score_risk_rules(
    alerts: list[dict[str, Any]],
    assets_by_id: dict[str, Any],
) -> dict[str, Any]:
    """Score each alert by severity × asset criticality and rank priorities.

    Args:
        alerts: Normalized alert dicts.
        assets_by_id: Mapping asset_id -> inventory row.
    """
    scored = []
    for alert in alerts:
        sev = (alert.get("severity") or "unknown").lower()
        asset_id = alert.get("dst_asset")
        asset = assets_by_id.get(asset_id) or {}
        crit = int(asset.get("criticality", 1))
        base = SEVERITY_WEIGHT.get(sev, 2)
        risk = round(base * 0.6 + crit * 0.8, 2)
        scored.append(
            {
                "alert_id": alert.get("alert_id"),
                "severity": sev,
                "asset_id": asset_id,
                "asset_criticality": crit,
                "risk_score": risk,
                "priority": "P1" if risk >= 6.5 else "P2" if risk >= 4.5 else "P3",
                "msg": alert.get("msg"),
            }
        )

    scored.sort(key=lambda x: x["risk_score"], reverse=True)
    p1 = sum(1 for s in scored if s["priority"] == "P1")
    p2 = sum(1 for s in scored if s["priority"] == "P2")
    avg = round(sum(s["risk_score"] for s in scored) / max(len(scored), 1), 2)

    return {
        "tool": "score_risk_rules",
        "scored_alerts": scored,
        "top_priorities": scored[:5],
        "counts": {"P1": p1, "P2": p2, "P3": len(scored) - p1 - p2},
        "avg_risk": avg,
        "summary": (
            f"Risque moyen {avg}. Priorités: P1={p1}, P2={p2}, "
            f"P3={len(scored) - p1 - p2}. Top: "
            + ", ".join(s["alert_id"] for s in scored[:3])
        ),
    }
