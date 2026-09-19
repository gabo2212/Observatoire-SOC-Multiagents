"""CrewAI agent factories for the SOC observatory."""
from __future__ import annotations

from crewai import Agent, LLM

import config


def make_llm() -> LLM:
    return LLM(
        model=f"openai/{config.LLM_MODEL}",
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_API_BASE,
        temperature=0.5,
        max_tokens=700,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


def build_all_agents(llm: LLM | None = None) -> dict[str, Agent]:
    llm = llm or make_llm()
    roles = config.AGENT_ROLES
    stories = {
        "coordinateur": "Tu diriges le SOC synthétique ACME-LAB et décomposes la mission.",
        "collecteur": "Tu agrèges journaux d'alertes synthétiques et inventaire d'actifs.",
        "classificateur": "Tu classifies type, gravité et faux positifs probables.",
        "correlateur": "Tu regroupes les alertes en campagnes et chaînes d'attaque.",
        "evaluateur": "Tu vérifies la cohérence et le risque métier.",
        "rapporteur": "Tu rédiges le brief final P1/P2/P3 pour l'analyste.",
    }
    return {
        key: Agent(
            role=meta["role"],
            goal=meta["goal"],
            backstory=stories[key],
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )
        for key, meta in roles.items()
    }
