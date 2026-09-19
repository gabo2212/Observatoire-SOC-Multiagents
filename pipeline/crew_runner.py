"""CrewAI-based SOC triage pipeline with full observability traces."""
from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task

import config
from pipeline.live_status import write_live
from pipeline.llm import estimate_cost, llm_ready
from pipeline.tracing import StepTrace, TraceStore
from tools.alerts import parse_alert_log
from tools.inventory import assets_for_alerts, lookup_asset_inventory
from tools.risk_rules import score_risk_rules

ProgressCb = Callable[[dict[str, Any]], None]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_llm() -> LLM:
    return LLM(
        model=f"openai/{config.LLM_MODEL}",
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_API_BASE,
        temperature=0.5,
        max_tokens=700,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


def _quality_from_text(text: str, risk: dict[str, Any] | None = None) -> float:
    score = 0.55
    if text and len(text) > 120:
        score += 0.15
    if risk:
        score += min(0.2, 0.04 * risk.get("counts", {}).get("P1", 0))
    if any(k in text.lower() for k in ("priorit", "p1", "recommand", "faux positif")):
        score += 0.1
    return round(min(score, 0.98), 2)


class SOCObservatoryCrew:
    """Sequential multi-agent SOC triage with instrumented steps."""

    AGENT_FLOW = [
        ("coordinateur", "collecteur"),
        ("collecteur", "classificateur"),
        ("classificateur", "correlateur"),
        ("correlateur", "evaluateur"),
        ("evaluateur", "rapporteur"),
    ]

    def __init__(self, store: TraceStore | None = None) -> None:
        self.store = store or TraceStore()
        self.llm = build_llm()

    def _emit(self, cb: ProgressCb | None, event: dict[str, Any]) -> None:
        write_live(event)
        if cb:
            cb(event)

    def _make_agents(self) -> dict[str, Agent]:
        roles = config.AGENT_ROLES
        return {
            "coordinateur": Agent(
                role=roles["coordinateur"]["role"],
                goal=roles["coordinateur"]["goal"],
                backstory=(
                    "Tu diriges un SOC synthétique ACME-LAB. Tu décomposes la "
                    "mission de triage sans inventer de données hors contexte."
                ),
                llm=self.llm,
                verbose=False,
                allow_delegation=False,
            ),
            "collecteur": Agent(
                role=roles["collecteur"]["role"],
                goal=roles["collecteur"]["goal"],
                backstory=(
                    "Tu agrèges des journaux d'alertes synthétiques et le "
                    "contexte d'inventaire des actifs."
                ),
                llm=self.llm,
                verbose=False,
                allow_delegation=False,
            ),
            "classificateur": Agent(
                role=roles["classificateur"]["role"],
                goal=roles["classificateur"]["goal"],
                backstory=(
                    "Tu classifies les alertes par type MITRE-like, gravité et "
                    "confiance. Tu signales les faux positifs probables."
                ),
                llm=self.llm,
                verbose=False,
                allow_delegation=False,
            ),
            "correlateur": Agent(
                role=roles["correlateur"]["role"],
                goal=roles["correlateur"]["goal"],
                backstory=(
                    "Tu regroupes les alertes en campagnes (même IP, même "
                    "utilisateur, même chaîne d'attaque)."
                ),
                llm=self.llm,
                verbose=False,
                allow_delegation=False,
            ),
            "evaluateur": Agent(
                role=roles["evaluateur"]["role"],
                goal=roles["evaluateur"]["goal"],
                backstory=(
                    "Tu vérifies la cohérence du triage, confrontes les scores "
                    "règle-based et estimes le risque métier."
                ),
                llm=self.llm,
                verbose=False,
                allow_delegation=False,
            ),
            "rapporteur": Agent(
                role=roles["rapporteur"]["role"],
                goal=roles["rapporteur"]["goal"],
                backstory=(
                    "Tu rédiges un brief SOC actionnable: priorités P1/P2/P3, "
                    "actions et limites."
                ),
                llm=self.llm,
                verbose=False,
                allow_delegation=False,
            ),
        }

    def run_scenario(
        self,
        scenario_key: str,
        *,
        force_tools_only: bool = False,
        on_progress: ProgressCb | None = None,
        alert_file: str | None = None,
        mission_override: str | None = None,
        label_override: str | None = None,
    ) -> dict[str, Any]:
        # Allow one-shot custom missions (user sites) without editing config
        if scenario_key not in config.SCENARIOS and not alert_file:
            raise KeyError(f"Unknown scenario: {scenario_key}")

        if scenario_key in config.SCENARIOS:
            meta = dict(config.SCENARIOS[scenario_key])
        else:
            meta = {
                "label": label_override or "Mission personnalisée",
                "mission": mission_override or "Trier les alertes sur les actifs sélectionnés.",
                "alert_file": alert_file,
            }
        if alert_file:
            meta["alert_file"] = alert_file
        if mission_override:
            meta["mission"] = mission_override
        if label_override:
            meta["label"] = label_override

        mission = meta["mission"]
        alert_file = meta["alert_file"]
        model = config.MODEL_DISPLAY
        total_steps = 6

        run_id = self.store.start_run(
            scenario_key, mission, model, scenario_label=meta.get("label")
        )
        self._emit(
            on_progress,
            {
                "state": "running",
                "run_id": run_id,
                "scenario": scenario_key,
                "scenario_label": meta["label"],
                "mission": mission,
                "step_index": 0,
                "total_steps": total_steps,
                "agent": None,
                "phase": "start",
                "message": f"Mission démarrée — {meta['label']}",
                "completed_agents": [],
                "latest_output": "",
                "used_llm": None,
            },
        )

        steps: list[StepTrace] = []
        context: dict[str, Any] = {"scenario": scenario_key, "mission": mission}
        totals = {
            "duration_s": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "error_count": 0,
            "retry_count": 0,
        }
        completed_agents: list[str] = []

        self._emit(
            on_progress,
            {
                "state": "running",
                "run_id": run_id,
                "scenario": scenario_key,
                "scenario_label": meta["label"],
                "mission": mission,
                "step_index": 0,
                "total_steps": total_steps,
                "agent": "collecteur",
                "phase": "tools",
                "message": "Outils: lecture des alertes, inventaire, score de risque…",
                "completed_agents": completed_agents,
                "latest_output": "",
            },
        )
        try:
            parsed = parse_alert_log(alert_file)
            asset_ids = assets_for_alerts(parsed["alerts"])
            inventory = lookup_asset_inventory(asset_ids)
            risk = score_risk_rules(parsed["alerts"], inventory["by_id"])
            context.update({"parsed": parsed, "inventory": inventory, "risk": risk})
            tool_status = "success"
            tool_errors: list[str] = []
            tool_summary = (
                f"{parsed['summary']} | {inventory['summary']} | {risk['summary']}"
            )
        except Exception as exc:  # noqa: BLE001
            tool_status = "error"
            tool_errors = [str(exc)]
            tool_summary = f"Échec outils: {exc}"
            risk = None
            totals["error_count"] += 1

        agent_specs = [
            (
                "coordinateur",
                "Plan de triage",
                (
                    f"Mission: {mission}\n"
                    f"Scénario: {meta['label']}\n"
                    "Produis un plan court en 4-6 puces: ordre des agents, "
                    "données à collecter, critères de priorisation. Pas de jargon inutile."
                ),
                ["collecteur"],
                [],
            ),
            (
                "collecteur",
                "Synthèse de collecte",
                lambda: (
                    f"Voici le résultat des outils:\n{tool_summary}\n"
                    f"Nombre d'alertes: {context.get('parsed', {}).get('alert_count')}\n"
                    "Résume les faits observables pour le classificateur (5 puces max)."
                ),
                ["classificateur"],
                ["parse_alert_log", "lookup_asset_inventory"],
            ),
            (
                "classificateur",
                "Classification des alertes",
                lambda: (
                    "Classifie les alertes suivantes (type, gravité confirmée, "
                    "faux positif probable oui/non):\n"
                    + json.dumps(context.get("parsed", {}).get("alerts", [])[:8], ensure_ascii=False)
                    + "\nRéponds de façon structurée et concise."
                ),
                ["correlateur"],
                [],
            ),
            (
                "correlateur",
                "Corrélation de campagne",
                lambda: (
                    "À partir des alertes et de la classification précédente, "
                    "identifie 1-3 campagnes/corrélations (IP, user, chaîne). "
                    f"Alertes: {json.dumps(context.get('parsed', {}).get('alerts', [])[:8], ensure_ascii=False)}"
                ),
                ["evaluateur"],
                [],
            ),
            (
                "evaluateur",
                "Évaluation et vérification",
                lambda: (
                    "Vérifie la cohérence du triage. Scores règles:\n"
                    + json.dumps(context.get("risk", {}), ensure_ascii=False)[:2500]
                    + "\nConfirme ou ajuste les priorités P1/P2/P3 et note un score de confiance 0-1."
                ),
                ["rapporteur"],
                ["score_risk_rules"],
            ),
            (
                "rapporteur",
                "Rapport final de priorisation",
                lambda: (
                    f"Mission: {mission}\n"
                    f"Scores: {context.get('risk', {}).get('summary')}\n"
                    "Rédige le brief final: résumé, top 3 actions, alertes P1, "
                    "limites (données synthétiques)."
                ),
                [],
                [],
            ),
        ]

        use_llm = (not force_tools_only) and llm_ready()
        previous_outputs: list[str] = []
        final_text = tool_summary
        step_index = 0

        for name, task_name, prompt_obj, next_agents, tools_used in agent_specs:
            role = config.AGENT_ROLES[name]["role"]
            self._emit(
                on_progress,
                {
                    "state": "running",
                    "run_id": run_id,
                    "scenario": scenario_key,
                    "scenario_label": meta["label"],
                    "mission": mission,
                    "step_index": step_index,
                    "total_steps": total_steps,
                    "agent": name,
                    "agent_role": role,
                    "task": task_name,
                    "phase": "agent_start",
                    "message": f"En cours: {role} — {task_name}",
                    "completed_agents": list(completed_agents),
                    "latest_output": previous_outputs[-1] if previous_outputs else tool_summary[:400],
                    "used_llm": use_llm,
                    "progress": step_index / total_steps,
                },
            )

            start = _now()
            t0 = time.perf_counter()
            retries = 0
            errors: list[str] = []
            tokens_in = tokens_out = 0
            status = "success"
            output = ""

            prompt = prompt_obj() if callable(prompt_obj) else prompt_obj
            if previous_outputs:
                prompt = (
                    prompt
                    + "\n\nContexte agents précédents:\n"
                    + "\n---\n".join(previous_outputs[-2:])
                )

            if use_llm:
                try:
                    agents = self._make_agents()
                    task = Task(
                        description=prompt,
                        expected_output="Réponse concise en français (max 250 mots).",
                        agent=agents[name],
                    )
                    crew = Crew(
                        agents=[agents[name]],
                        tasks=[task],
                        process=Process.sequential,
                        verbose=False,
                    )
                    result = crew.kickoff()
                    output = str(result).strip()
                    tokens_in = max(80, len(prompt) // 4)
                    tokens_out = max(40, len(output) // 4)
                except Exception as exc:  # noqa: BLE001
                    retries = 1
                    totals["retry_count"] += 1
                    errors.append(str(exc))
                    try:
                        from pipeline.llm import chat

                        lr = chat(
                            [
                                {"role": "system", "content": f"Tu es l'agent {name} d'un SOC."},
                                {"role": "user", "content": prompt},
                            ],
                            max_tokens=500,
                            temperature=0.4,
                        )
                        output = lr.content
                        tokens_in = lr.tokens_in
                        tokens_out = lr.tokens_out
                        errors.append("crewai_fallback_openai_client")
                    except Exception as exc2:  # noqa: BLE001
                        status = "error"
                        errors.append(str(exc2))
                        output = f"[erreur agent {name}] {exc2}"
                        totals["error_count"] += 1
            else:
                output = self._offline_agent_output(name, context, meta)
                tokens_in, tokens_out = 120, 180
                if name == "collecteur" and tool_status != "success":
                    status = "error"

            end = _now()
            dur = time.perf_counter() - t0
            cost = estimate_cost(tokens_in, tokens_out)
            q = _quality_from_text(output, context.get("risk"))

            tools = list(tools_used)
            tool_calls = len(tools)
            if name == "collecteur":
                tools = [
                    "parse_alert_log",
                    "lookup_asset_inventory",
                    "score_risk_rules",
                ]
                tool_calls = 3
                if tool_errors:
                    errors.extend(tool_errors)
                    if tool_status != "success":
                        status = "error"

            step = StepTrace(
                agent=name,
                task=task_name,
                status=status,
                model=model,
                start_time=start,
                end_time=end,
                duration_s=round(dur, 3),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost,
                tools_used=tools,
                tool_calls=tool_calls,
                retries=retries,
                errors=errors,
                result_summary=output[:500],
                quality_score=q,
                messages_to=next_agents,
                raw_output=output,
            )
            self.store.add_step(run_id, step_index, step)
            steps.append(step)
            completed_agents.append(name)
            step_index += 1

            totals["duration_s"] += dur
            totals["tokens_in"] += tokens_in
            totals["tokens_out"] += tokens_out
            totals["cost_usd"] += cost
            previous_outputs.append(f"[{name}] {output[:800]}")
            final_text = output

            self._emit(
                on_progress,
                {
                    "state": "running",
                    "run_id": run_id,
                    "scenario": scenario_key,
                    "scenario_label": meta["label"],
                    "mission": mission,
                    "step_index": step_index,
                    "total_steps": total_steps,
                    "agent": name,
                    "agent_role": role,
                    "task": task_name,
                    "phase": "agent_done",
                    "message": f"Terminé: {role} ({dur:.1f}s)",
                    "completed_agents": list(completed_agents),
                    "latest_output": output[:1200],
                    "step_status": status,
                    "used_llm": use_llm,
                    "progress": step_index / total_steps,
                },
            )

        run_status = "success" if totals["error_count"] == 0 else "partial"
        if all(s.status == "error" for s in steps):
            run_status = "failed"

        quality = _quality_from_text(final_text, context.get("risk"))
        self.store.finish_run(
            run_id,
            status=run_status,
            final_result=final_text,
            quality_score=quality,
            totals={
                "duration_s": round(totals["duration_s"], 3),
                "tokens_in": totals["tokens_in"],
                "tokens_out": totals["tokens_out"],
                "cost_usd": round(totals["cost_usd"], 6),
                "error_count": totals["error_count"],
                "retry_count": totals["retry_count"],
            },
        )

        result = {
            "run_id": run_id,
            "status": run_status,
            "scenario": scenario_key,
            "quality_score": quality,
            "final_result": final_text,
            "used_llm": use_llm,
            "totals": totals,
        }
        self._emit(
            on_progress,
            {
                "state": "done",
                "run_id": run_id,
                "scenario": scenario_key,
                "scenario_label": meta["label"],
                "mission": mission,
                "step_index": total_steps,
                "total_steps": total_steps,
                "agent": "rapporteur",
                "phase": "finished",
                "message": f"Mission terminée ({run_status})",
                "completed_agents": completed_agents,
                "latest_output": final_text[:2000],
                "result": result,
                "used_llm": use_llm,
                "progress": 1.0,
            },
        )
        return result

    def _offline_agent_output(
        self, name: str, context: dict[str, Any], meta: dict[str, Any]
    ) -> str:
        risk = context.get("risk") or {}
        parsed = context.get("parsed") or {}
        if name == "coordinateur":
            return (
                f"Plan triage — {meta['label']}: 1) collecter alertes 2) classer "
                "3) corréler 4) scorer risque 5) rapporter priorités P1/P2/P3."
            )
        if name == "collecteur":
            return parsed.get("summary", "Collecte indisponible") + " | " + (
                context.get("inventory") or {}
            ).get("summary", "")
        if name == "classificateur":
            sev = parsed.get("severity_breakdown", {})
            return f"Classification: répartition gravité {sev}. Signal fort si critical/high dominant."
        if name == "correlateur":
            return (
                "Corrélation: regrouper par src_ip et user; chaînes auth→privilège "
                "ou phishing→MFA→forward rule selon le scénario."
            )
        if name == "evaluateur":
            return risk.get("summary", "Évaluation indisponible") + (
                f" Top: {risk.get('top_priorities', [])[:3]}"
            )
        return (
            f"Brief {meta['label']}: {risk.get('summary', '')}. "
            "Actions: isoler actifs P1, révoquer sessions, rehausser règles IDS bruyantes. "
            "Limite: journaux synthétiques ACME-LAB."
        )
