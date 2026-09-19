"""Plotly chart builders for the SOC observatory dashboard."""
from __future__ import annotations

from typing import Any

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import config

AGENT_ORDER = [
    "coordinateur",
    "collecteur",
    "classificateur",
    "correlateur",
    "evaluateur",
    "rapporteur",
]

EDGES = [
    ("coordinateur", "collecteur"),
    ("collecteur", "classificateur"),
    ("classificateur", "correlateur"),
    ("correlateur", "evaluateur"),
    ("evaluateur", "rapporteur"),
]


def agent_color(name: str) -> str:
    return config.AGENT_ROLES.get(name, {}).get("color", "#64748b")


def fig_agent_graph(active_agent: str | None = None, steps: pd.DataFrame | None = None) -> go.Figure:
    g = nx.DiGraph()
    g.add_nodes_from(AGENT_ORDER)
    g.add_edges_from(EDGES)
    pos = {
        "coordinateur": (0, 1),
        "collecteur": (1, 1),
        "classificateur": (2, 1.2),
        "correlateur": (3, 0.8),
        "evaluateur": (4, 1),
        "rapporteur": (5, 1),
    }

    edge_x, edge_y = [], []
    for a, b in EDGES:
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    node_x, node_y, texts, colors, sizes = [], [], [], [], []
    for n in AGENT_ORDER:
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        role = config.AGENT_ROLES[n]["role"]
        texts.append(f"{role}<br>({n})")
        colors.append("#f59e0b" if active_agent == n else agent_color(n))
        sizes.append(34 if active_agent == n else 26)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=2, color="#94a3b8"),
            hoverinfo="none",
            name="communications",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            marker=dict(size=sizes, color=colors, line=dict(width=2, color="#0f172a")),
            text=[config.AGENT_ROLES[n]["role"].split()[0] for n in AGENT_ORDER],
            textposition="top center",
            hovertext=texts,
            hoverinfo="text",
            name="agents",
        )
    )
    fig.update_layout(
        title="Graphe interactif du système multiagents SOC",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=360,
        margin=dict(l=20, r=20, t=50, b=20),
        plot_bgcolor="#f8fafc",
    )
    return fig


def fig_timeline(steps: pd.DataFrame) -> go.Figure:
    if steps.empty:
        return go.Figure()
    df = steps.copy()
    df = df.sort_values("step_index")
    # Build cumulative Gantt within the run using duration
    records = []
    cursor = 0.0
    for _, row in df.iterrows():
        start = cursor
        end = cursor + float(row["duration_s"] or 0.01)
        records.append(
            {
                "Agent": row["agent"],
                "Start": start,
                "Finish": end,
                "Task": row["task"],
                "Durée (s)": row["duration_s"],
            }
        )
        cursor = end
    gdf = pd.DataFrame(records)
    fig = px.bar(
        gdf,
        x="Durée (s)",
        y="Agent",
        color="Agent",
        orientation="h",
        hover_data=["Task", "Start", "Finish"],
        color_discrete_map={a: agent_color(a) for a in AGENT_ORDER},
        title="Timeline / cascade des étapes (durée par agent)",
    )
    fig.update_layout(height=380, xaxis_title="Durée (secondes)", yaxis_title="Agent")
    return fig


def fig_sankey(steps: pd.DataFrame) -> go.Figure:
    if steps.empty:
        return go.Figure()
    # Token flow along the pipeline edges
    labels = AGENT_ORDER
    idx = {n: i for i, n in enumerate(labels)}
    source, target, value = [], [], []
    by_agent = steps.groupby("agent")[["tokens_in", "tokens_out"]].sum()
    for a, b in EDGES:
        if a in by_agent.index:
            v = float(by_agent.loc[a, "tokens_out"] + by_agent.loc[a, "tokens_in"] * 0.25)
            v = max(v, 1)
            source.append(idx[a])
            target.append(idx[b])
            value.append(v)
    fig = go.Figure(
        go.Sankey(
            node=dict(
                label=[config.AGENT_ROLES[n]["role"] for n in labels],
                color=[agent_color(n) for n in labels],
                pad=18,
                thickness=18,
            ),
            link=dict(source=source, target=target, value=value),
        )
    )
    fig.update_layout(
        title="Sankey — circulation des jetons / messages entre agents",
        height=400,
        margin=dict(t=50, l=20, r=20, b=20),
    )
    return fig


def fig_compare_agents(steps: pd.DataFrame, metric: str = "duration_s") -> go.Figure:
    if steps.empty:
        return go.Figure()
    agg = (
        steps.groupby("agent")
        .agg(
            duration_s=("duration_s", "mean"),
            tokens=("tokens_out", "sum"),
            quality_score=("quality_score", "mean"),
            errors=("status", lambda s: (s == "error").sum()),
            cost_usd=("cost_usd", "sum"),
        )
        .reindex(AGENT_ORDER)
        .dropna(how="all")
        .reset_index()
    )
    label_map = {
        "duration_s": "Durée moyenne (s)",
        "tokens": "Jetons en sortie",
        "quality_score": "Score qualité",
        "cost_usd": "Coût estimé (USD)",
        "errors": "Erreurs",
    }
    y = metric if metric in agg.columns else "duration_s"
    fig = px.bar(
        agg,
        x="agent",
        y=y,
        color="agent",
        color_discrete_map={a: agent_color(a) for a in AGENT_ORDER},
        title=f"Comparatif par agent — {label_map.get(y, y)}",
        labels={"agent": "Agent", y: label_map.get(y, y)},
    )
    fig.update_layout(showlegend=False, height=380)
    return fig


def fig_heatmap(steps: pd.DataFrame, value: str = "duration_s") -> go.Figure:
    if steps.empty:
        return go.Figure()
    df = steps.copy()
    if value == "errors":
        df["val"] = (df["status"] == "error").astype(int)
        title = "Carte thermique — erreurs par scénario × agent"
    else:
        df["val"] = df["duration_s"]
        title = "Carte thermique — latence moyenne (s) par scénario × agent"
    pivot = df.pivot_table(
        index="scenario_label",
        columns="agent",
        values="val",
        aggfunc="mean",
    )
    pivot = pivot.reindex(columns=[c for c in AGENT_ORDER if c in pivot.columns])
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="YlOrRd",
        title=title,
        labels=dict(color="Valeur"),
    )
    fig.update_layout(height=420)
    return fig


def interpretation_bullets(runs: pd.DataFrame, steps: pd.DataFrame) -> list[str]:
    if runs.empty or steps.empty:
        return ["Aucune donnée — lancez `python -m scripts.run_batch`."]
    tokens = steps.groupby("agent")[["tokens_in", "tokens_out"]].sum()
    tokens["total"] = tokens["tokens_in"] + tokens["tokens_out"]
    top_tok = tokens["total"].idxmax()
    slow = steps.groupby("agent")["duration_s"].mean().idxmax()
    err = steps.assign(is_err=(steps["status"] == "error")).groupby("agent")["is_err"].sum()
    top_err = err.idxmax() if err.sum() else "aucun"
    retries = int(steps["retries"].sum())
    corr_txt = "non calculable (coût local toujours 0)"
    if len(runs) > 2 and float(runs["total_cost_usd"].std() or 0) > 0:
        corr = float(runs["total_cost_usd"].corr(runs["quality_score"]))
        corr_txt = f"{corr:.2f}"
    return [
        f"Agent le plus consommateur de jetons: **{top_tok}** ({int(tokens.loc[top_tok, 'total'])} jetons).",
        f"Agent le plus lent (durée moyenne): **{slow}** ({steps.groupby('agent')['duration_s'].mean().loc[slow]:.2f} s).",
        f"Agent avec le plus d'erreurs: **{top_err}**.",
        f"Tentatives / retries cumulés: **{retries}** — surtout sur les appels LLM locaux.",
        f"Corrélation coût↔qualité (Pearson): **{corr_txt}**.",
        "Goulot principal: étapes LLM longues (évaluateur/rapporteur) vs outils quasi instantanés.",
        "Communications utiles: chaîne coord→…→rapport; peu de boucles inutiles dans ce flux séquentiel.",
        "Levier coût: raccourcir max_tokens et désactiver le thinking Qwen (`enable_thinking=false`).",
        "Levier qualité: enrichir `score_risk_rules` et forcer une validation P1 avant le rapport final.",
    ]
