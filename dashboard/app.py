"""
Observatoire interactif — triage multiagents d'alertes SOC (sujet A5).
Lancement depuis l'UI + suivi live des agents.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from dashboard.charts import (
    AGENT_ORDER,
    fig_agent_graph,
    fig_compare_agents,
    fig_heatmap,
    fig_sankey,
    fig_timeline,
    interpretation_bullets,
)
from dashboard.data_loader import filter_runs, get_store, kpi_dict, runs_df, steps_df
from pipeline.crew_runner import SOCObservatoryCrew
from pipeline.datasets import (
    ensure_runtime_files,
    import_alerts_json,
    import_dataset_zip,
    list_datasets,
)
from pipeline.live_status import read_live
from pipeline.llm import llm_ready
from pipeline.seed import ensure_demo_data
from tools.sites import (
    add_user_site,
    build_alerts_for_targets,
    delete_user_site,
    load_full_inventory,
    load_user_sites,
)

st.set_page_config(page_title=config.PROJECT_TITLE, layout="wide")

# Persist UI choices across reruns
if "focus_run" not in st.session_state:
    st.session_state.focus_run = None
if "live_log" not in st.session_state:
    st.session_state.live_log = []


def chart(fig, key: str) -> None:
    st.plotly_chart(
        fig,
        width="stretch",
        key=key,
        config={"displayModeBar": False, "responsive": True},
    )


_live_tick = 0


def live_chart(fig) -> None:
    """Chart inside live callback — must get a fresh key each update."""
    global _live_tick
    _live_tick += 1
    st.plotly_chart(
        fig,
        width="stretch",
        key=f"live_graph_{_live_tick}",
        config={"displayModeBar": False, "responsive": True},
    )


def agent_checklist(completed: list[str], active: str | None) -> None:
    cols = st.columns(len(AGENT_ORDER))
    for col, key in zip(cols, AGENT_ORDER):
        role = config.AGENT_ROLES[key]["role"]
        if key in completed:
            col.success(f"OK\n\n**{role}**")
        elif key == active:
            col.warning(f"…\n\n**{role}**")
        else:
            col.info(f"○\n\n**{role}**")


def friendly_run_label(run: dict) -> str:
    label = run.get("scenario_label") or run.get("scenario")
    short = (run.get("run_id") or "")[-8:]
    return f"{label} · {run.get('status')} · …{short}"


def studio_chrome(llm_online: bool) -> None:
    css = (Path(__file__).parent / "studio.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    pill = (
        '<span class="vis-pill vis-pill-on">LLM en ligne</span>'
        if llm_online
        else '<span class="vis-pill vis-pill-off">LLM hors ligne</span>'
    )
    st.markdown(
        f"""
<div class="vis-bar">
  <div class="vis-brand">
    <svg width="28" height="28" viewBox="0 0 64 64" aria-hidden="true">
      <g fill="#111">
        <rect x="28" y="6" width="8" height="52" rx="2"/>
        <rect x="28" y="6" width="8" height="52" rx="2" transform="rotate(60 32 32)"/>
        <rect x="28" y="6" width="8" height="52" rx="2" transform="rotate(120 32 32)"/>
      </g>
    </svg>
    <span>Observatoire</span>
  </div>
  {pill}
</div>
        """,
        unsafe_allow_html=True,
    )


# ── Header ──────────────────────────────────────────────
ready = llm_ready()
studio_chrome(ready)

if not ready:
    st.warning(
        "Démarrez le modèle: `bash scripts/start_llm.sh` — "
        "sinon utilisez le mode **Rapide** dans l'onglet Lancer."
    )

store = get_store()
ensure_demo_data(store)

tab_launch, tab_analyze, tab_compare = st.tabs(["Lancer", "Résultat", "Comparer"])

# ════════════════════════════════════════════════════════
# Lancer
# ════════════════════════════════════════════════════════
with tab_launch:
    st.markdown(
        '<p class="vis-kicker">Mission</p><h2 class="vis-page">Lancer</h2>',
        unsafe_allow_html=True,
    )

    mission_mode = st.radio(
        "Type de mission",
        [
            "Dataset (recommandé)",
            "Scénario démo (ACME-LAB)",
            "Mes sites (cibles personnalisées)",
        ],
        horizontal=True,
    )

    custom_targets: list[str] = []
    scenario = list(config.SCENARIOS.keys())[0]
    selected_ds = st.session_state.get("selected_dataset")
    pattern = ("web_probe", "Sondes web")

    if mission_mode.startswith("Dataset"):
        datasets = [d for d in list_datasets() if d["compatible"]]
        if not datasets:
            st.error("Aucun dataset compatible.")
        else:
            ids = [d["id"] for d in datasets]
            default_i = ids.index(selected_ds) if selected_ds in ids else 0
            selected_ds = st.selectbox(
                "Dataset",
                ids,
                index=default_i,
                format_func=lambda i: next(
                    f"{d.get('name')} — {d['validation']['alert_count']} alertes"
                    for d in datasets
                    if d["id"] == i
                ),
                key="launch_dataset",
            )
            st.session_state.selected_dataset = selected_ds
            meta = next(d for d in datasets if d["id"] == selected_ds)
            if meta.get("mission"):
                st.caption(meta["mission"])
    elif mission_mode.startswith("Scénario"):
        scenario_keys = list(config.SCENARIOS.keys())
        labels = {k: config.SCENARIOS[k]["label"] for k in scenario_keys}
        scenario = st.selectbox(
            "Scénario",
            scenario_keys,
            format_func=lambda k: labels[k],
            key="launch_scenario",
        )
        st.caption(config.SCENARIOS[scenario]["mission"])
    else:
        inventory = load_full_inventory()
        user_only = [a for a in inventory if a.get("source") == "user"]
        choices = user_only or inventory
        if not user_only:
            st.caption("Pas encore de site personnel. Ajoutez-en un plus bas, ou prenez des actifs du lab.")
        options = {a["asset_id"]: a for a in choices}
        custom_targets = st.multiselect(
            "Cibles",
            options=list(options.keys()),
            default=list(options.keys())[: min(3, len(options))],
            format_func=lambda aid: (
                f"{options[aid].get('name') or options[aid]['hostname']} "
                f"(crit. {options[aid]['criticality']})"
            ),
        )
        pattern = st.selectbox(
            "Type d'alertes",
            [
                ("web_probe", "Sondes web"),
                ("bruteforce", "Brute-force"),
                ("exfil", "Exfiltration"),
            ],
            format_func=lambda x: x[1],
        )

    mode = st.radio(
        "Mode",
        ["LLM local", "Rapide"],
        horizontal=True,
        help="LLM local attend le modèle. Rapide enchaîne les outils sans lui.",
    )
    use_offline = mode.startswith("Rapide") or not ready
    start = st.button("Démarrer le triage", type="primary")

    with st.expander("Ajouter une cible"):
        with st.form("add_site_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                hostname = st.text_input("Domaine ou hostname", placeholder="boutique.mondomaine.com")
                name = st.text_input("Nom affiché", placeholder="Boutique prod")
            with c2:
                site_type = st.selectbox(
                    "Type",
                    ["web_server", "api", "database", "mail", "vpn_gateway", "workstation", "other"],
                )
                criticality = st.slider("Criticité", 1, 5, 4)
                zone = st.selectbox("Zone", ["dmz", "internal", "edge", "restricted", "cloud"])
            submitted = st.form_submit_button("Ajouter")
        if submitted:
            try:
                row = add_user_site(
                    hostname=hostname,
                    name=name or None,
                    site_type=site_type,
                    criticality=criticality,
                    zone=zone,
                )
                st.success(f"Ajouté : {row['hostname']}")
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
        user_sites = load_user_sites()
        if user_sites:
            st.dataframe(user_sites, width="stretch")
            del_id = st.selectbox(
                "Retirer",
                [s["asset_id"] for s in user_sites],
                format_func=lambda x: next(
                    f"{s.get('name') or s['hostname']}" for s in user_sites if s["asset_id"] == x
                ),
            )
            if st.button("Retirer cette cible"):
                delete_user_site(del_id)
                st.rerun()

    with st.expander("Importer un dataset"):
        st.caption("alerts.json, alerts.json + assets.json, ou un zip.")
        up_alerts = st.file_uploader("alerts.json", type=["json"], key="up_alerts")
        up_assets = st.file_uploader("assets.json", type=["json"], key="up_assets")
        up_zip = st.file_uploader("dataset.zip", type=["zip"], key="up_zip")
        import_name = st.text_input("Nom", value="Mon import")
        if st.button("Importer"):
            if up_zip is not None:
                imported = import_dataset_zip(up_zip.getvalue(), fallback_name=import_name)
            elif up_alerts is not None:
                imported = import_alerts_json(
                    up_alerts.getvalue(),
                    name=import_name,
                    assets_raw=up_assets.getvalue() if up_assets else None,
                )
            else:
                imported = {"ok": False, "validation": {"errors": ["Ajoutez un JSON ou un ZIP."]}}
            if imported.get("ok"):
                st.session_state.selected_dataset = imported["dataset_id"]
                st.success(f"Importé : {imported['dataset_id']}")
                st.rerun()
            else:
                st.error("Import refusé")
                st.json(imported.get("validation") or imported)

    if start:
        st.session_state.live_log = []
        crew = SOCObservatoryCrew(store=store)
        progress_bar = st.progress(0, text="Démarrage")
        status_line = st.empty()
        checklist_box = st.empty()
        graph_box = st.empty()
        output_box = st.empty()

        placeholders = {
            "progress": progress_bar,
            "status": status_line,
            "checklist": checklist_box,
            "graph": graph_box,
            "output": output_box,
        }

        def on_progress(event: dict) -> None:
            agent = event.get("agent")
            completed = event.get("completed_agents") or []
            prog = float(event.get("progress") or 0)
            msg = event.get("message") or ""
            placeholders["progress"].progress(min(max(prog, 0.02), 1.0), text=msg)
            placeholders["status"].info(msg)
            with placeholders["checklist"].container():
                agent_checklist(completed, agent if event.get("phase") == "agent_start" else None)
            with placeholders["graph"].container():
                live_chart(fig_agent_graph(active_agent=agent))
            latest = event.get("latest_output") or ""
            if latest and event.get("phase") in ("agent_done", "finished", "tools"):
                st.session_state.live_log.append(
                    f"**{event.get('agent_role') or event.get('agent') or 'Système'}** — {msg}\n\n{latest[:800]}"
                )
            with placeholders["output"].container():
                st.markdown("#### Journal live")
                for entry in reversed(st.session_state.live_log[-6:]):
                    st.markdown(entry)
                    st.divider()

        run_kwargs: dict = {
            "force_tools_only": use_offline,
            "on_progress": on_progress,
        }

        with st.spinner("Les agents travaillent… ne fermez pas cet onglet"):
            try:
                if mission_mode.startswith("Dataset"):
                    if not selected_ds:
                        raise ValueError("Choisissez un dataset.")
                    prepared = ensure_runtime_files(selected_ds)
                    run_kwargs.update(
                        {
                            "alert_file": prepared["alert_file"],
                            "label_override": prepared["label"],
                            "mission_override": prepared["mission"],
                        }
                    )
                    scenario = f"dataset_{selected_ds}"
                elif mission_mode.startswith("Mes"):
                    if not custom_targets:
                        raise ValueError("Sélectionnez au moins une cible.")
                    alert_path, _alerts = build_alerts_for_targets(
                        custom_targets, pattern=pattern[0]
                    )
                    hosts = [
                        a.get("hostname")
                        for a in load_full_inventory()
                        if a["asset_id"] in custom_targets
                    ]
                    run_kwargs.update(
                        {
                            "alert_file": str(alert_path),
                            "label_override": "Mission cibles personnelles",
                            "mission_override": (
                                "Trier et prioriser les alertes synthétiques visant: "
                                + ", ".join(hosts)
                                + ". Produire un brief P1/P2/P3 pour ces actifs."
                            ),
                        }
                    )
                    scenario = "user_custom"
                result = crew.run_scenario(scenario, **run_kwargs)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Échec de la mission: {exc}")
                result = None

        if result:
            st.session_state.focus_run = result["run_id"]
            progress_bar.progress(1.0, text="Terminé")
            status_line.success(
                f"Mission terminée · statut **{result['status']}** · "
                f"qualité {result['quality_score']} · id `{result['run_id']}`"
            )
            st.markdown("### Brief")
            st.write(result.get("final_result") or "")
            st.caption("Le détail est dans Résultat.")

    live = read_live()
    if not start and live.get("state") == "running":
        st.warning("Une mission semble déjà en cours (fichier live_status). Rafraîchissez la page.")
        st.json({k: live.get(k) for k in ("run_id", "scenario_label", "message", "agent", "progress")})

# ════════════════════════════════════════════════════════
# TAB 2 — Analyze
# ════════════════════════════════════════════════════════
with tab_analyze:
    runs = runs_df(store)
    steps = steps_df(store)

    if runs.empty:
        st.warning("Aucune exécution. Lancez une mission d'abord.")
    else:
        st.markdown(
            '<p class="vis-kicker">Relecture</p><h2 class="vis-page">Résultat</h2>',
            unsafe_allow_html=True,
        )
        runs_sorted = runs.sort_values("started_at", ascending=False)
        run_ids = runs_sorted["run_id"].tolist()
        default_idx = 0
        if st.session_state.focus_run in run_ids:
            default_idx = run_ids.index(st.session_state.focus_run)

        selected_run = st.selectbox(
            "Exécution",
            run_ids,
            index=default_idx,
            format_func=lambda rid: friendly_run_label(
                runs_sorted[runs_sorted["run_id"] == rid].iloc[0].to_dict()
            ),
        )
        st.session_state.focus_run = selected_run

        run_meta = store.get_run(selected_run) or {}
        run_steps = steps[steps["run_id"] == selected_run].sort_values("step_index")

        tokens = int(run_meta.get("total_tokens_in") or 0) + int(
            run_meta.get("total_tokens_out") or 0
        )
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Statut", run_meta.get("status") or "—")
        m2.metric("Qualité", run_meta.get("quality_score") or 0)
        m3.metric("Durée", f"{round(float(run_meta.get('total_duration_s') or 0), 1)} s")
        m4.metric("Jetons", f"{tokens:,}")

        max_step = max(int(run_steps["step_index"].max()) if not run_steps.empty else 0, 0)
        if max_step > 0:
            replay_idx = st.slider("Étape", 0, max_step, 0)
        else:
            replay_idx = 0
            st.caption("Cette exécution n'a qu'une seule étape — relecture indisponible.")

        active = None
        if not run_steps.empty:
            match = run_steps.loc[run_steps["step_index"] == replay_idx, "agent"]
            active = match.iloc[0] if len(match) else None

        chart(fig_agent_graph(active_agent=active), key="analyze_graph")
        agent_checklist(
            [a for a in AGENT_ORDER if not run_steps.empty and a in set(run_steps.loc[run_steps["step_index"] <= replay_idx, "agent"])],
            active,
        )

        c1, c2 = st.columns(2)
        with c1:
            chart(fig_timeline(run_steps), key="analyze_timeline")
        with c2:
            chart(fig_sankey(run_steps), key="analyze_sankey")

        if not run_steps.empty:
            step_row = run_steps[run_steps["step_index"] == replay_idx]
            if not step_row.empty:
                row = step_row.iloc[0]
                role = config.AGENT_ROLES.get(row["agent"], {}).get("role", row["agent"])
                st.markdown(f"### Étape {replay_idx}: {role}")
                st.write(
                    f"**Tâche:** {row['task']}  \n"
                    f"**Statut:** {row['status']} · **{row['duration_s']} s** · "
                    f"jetons {row['tokens_in']}→{row['tokens_out']}  \n"
                    f"**Outils:** {row['tools_used'] or 'aucun'}"
                )
                if row.get("errors"):
                    st.error(str(row["errors"]))
                st.text_area(
                    "Ce que l'agent a produit",
                    row.get("raw_output") or row.get("result_summary") or "",
                    height=200,
                )

        st.markdown("### Résultat final (brief SOC)")
        st.write(run_meta.get("final_result") or "—")

# ════════════════════════════════════════════════════════
# TAB 3 — Compare / KPIs
# ════════════════════════════════════════════════════════
with tab_compare:
    runs = runs_df(store)
    steps = steps_df(store)

    st.markdown(
        '<p class="vis-kicker">Synthèse</p><h2 class="vis-page">Comparer</h2>',
        unsafe_allow_html=True,
    )
    scenario_opts = sorted(runs["scenario"].unique()) if not runs.empty else []
    status_opts = sorted(runs["status"].unique()) if not runs.empty else []
    with st.expander("Filtres"):
        sel_scenarios = st.multiselect(
            "Scénarios", scenario_opts, default=scenario_opts, key="flt_sc"
        )
        sel_status = st.multiselect(
            "États", status_opts, default=status_opts, key="flt_st"
        )
        sel_agents = st.multiselect(
            "Agents", AGENT_ORDER, default=AGENT_ORDER, key="flt_ag"
        )

    runs_f = filter_runs(runs, scenarios=sel_scenarios or None, statuses=sel_status or None)
    run_id_set = set(runs_f["run_id"]) if not runs_f.empty else set()
    steps_f = steps[steps["run_id"].isin(run_id_set)] if not steps.empty else steps
    if sel_agents and not steps_f.empty:
        steps_f = steps_f[steps_f["agent"].isin(sel_agents)]

    kpis = kpi_dict(runs_f, steps_f)
    a, b, c, d = st.columns(4)
    a.metric("Exécutions", kpis["n_runs"])
    b.metric("Réussite", f"{kpis['success_rate']} %")
    c.metric("Durée moy.", f"{kpis['avg_duration']} s")
    d.metric("Jetons", f"{kpis['total_tokens']:,}")

    if runs_f.empty:
        st.info("Aucune donnée pour ces filtres.")
    else:
        metric = st.selectbox(
            "Comparer les agents sur…",
            ["duration_s", "tokens", "quality_score", "errors"],
            format_func=lambda x: {
                "duration_s": "Durée",
                "tokens": "Jetons",
                "quality_score": "Qualité",
                "errors": "Erreurs",
            }[x],
        )
        chart(fig_compare_agents(steps_f, metric=metric), key="compare_agents")

        heat_mode = st.radio("Carte thermique", ["Latence", "Erreurs"], horizontal=True)
        chart(
            fig_heatmap(
                steps_f, value="errors" if heat_mode == "Erreurs" else "duration_s"
            ),
            key="compare_heatmap",
        )

        st.markdown("#### Côte à côte")
        run_list = runs_f.sort_values("started_at", ascending=False)["run_id"].tolist()
        ca, cb = st.columns(2)
        with ca:
            run_a = st.selectbox(
                "A",
                run_list,
                format_func=lambda rid: friendly_run_label(
                    runs_f[runs_f["run_id"] == rid].iloc[0].to_dict()
                ),
                key="cmp_a",
            )
        with cb:
            run_b = st.selectbox(
                "B",
                run_list,
                index=min(1, len(run_list) - 1),
                format_func=lambda rid: friendly_run_label(
                    runs_f[runs_f["run_id"] == rid].iloc[0].to_dict()
                ),
                key="cmp_b",
            )
        ra, rb = store.get_run(run_a) or {}, store.get_run(run_b) or {}
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "run": "A",
                        "scénario": ra.get("scenario_label"),
                        "durée": ra.get("total_duration_s"),
                        "jetons": (ra.get("total_tokens_in") or 0)
                        + (ra.get("total_tokens_out") or 0),
                        "qualité": ra.get("quality_score"),
                        "erreurs": ra.get("error_count"),
                        "statut": ra.get("status"),
                    },
                    {
                        "run": "B",
                        "scénario": rb.get("scenario_label"),
                        "durée": rb.get("total_duration_s"),
                        "jetons": (rb.get("total_tokens_in") or 0)
                        + (rb.get("total_tokens_out") or 0),
                        "qualité": rb.get("quality_score"),
                        "erreurs": rb.get("error_count"),
                        "statut": rb.get("status"),
                    },
                ]
            ),
            width="stretch",
        )

        st.markdown("#### Lecture")
        for bullet in interpretation_bullets(runs_f, steps_f):
            st.markdown(f"- {bullet}")
