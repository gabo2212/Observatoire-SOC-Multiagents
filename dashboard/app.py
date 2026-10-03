"""
Observatoire interactif — triage multiagents d'alertes SOC (sujet A5).
Lancement depuis l'UI + suivi live des agents.
"""

#Claudia a ajouté un commentaire ici pour le fichier app.py
# Ce fichier contient le code principal de l'application Streamlit pour l'observatoire SOC multiagents.
# Importation des modules nécessaires et configuration du chemin d'accès racine.
# Ce fichier configure également le chemin d'accès racine pour permettre l'importation des modules locaux.
# Définition du chemin d'accès racine de l'application.
# Ce chemin est utilisé pour s'assurer que les modules locaux peuvent être importés correctement.

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
    schema_example,
    validate_dataset_payload,
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
    st.plotly_chart(fig, width="stretch", key=key)


_live_tick = 0


def live_chart(fig) -> None:
    """Chart inside live callback — must get a fresh key each update."""
    global _live_tick
    _live_tick += 1
    st.plotly_chart(fig, width="stretch", key=f"live_graph_{_live_tick}")


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


# ── Header ──────────────────────────────────────────────
st.title(config.PROJECT_TITLE)
st.caption(
    "Triage d'alertes cyber **synthétiques** · 6 agents qui se passent le relais · "
    "vous lancez une mission ici et voyez qui travaille en direct."
)

with st.expander("Comment ça marche ? (lire en 30 secondes)", expanded=False):
    st.markdown(
        """
1. Onglet **Mes sites** → ajoutez votre domaine (ex. `boutique.com`).
2. Onglet **Lancer** → mode **Mes sites** → cochez vos cibles → **Démarrer**.
3. Les agents trient des **alertes synthétiques** visant vos hostnames (pas un scan live).
4. Onglet **Analyser** → rejouez l'exécution; **Comparer** → KPI du cours.

**Modes:** *LLM local* (~1 min) ou *Rapide* (instantané).
        """
    )

ready = llm_ready()
c_llm, c_hint = st.columns([1, 3])
with c_llm:
    if ready:
        st.success("LLM local: en ligne (port 8080)")
    else:
        st.error("LLM local: hors ligne")
with c_hint:
    if not ready:
        st.warning(
            "Démarrez le modèle: `bash scripts/start_llm.sh` — "
            "sinon utilisez le mode **Rapide** dans l'onglet Lancer."
        )

store = get_store()
ensure_demo_data(store)

tab_sites, tab_data, tab_launch, tab_analyze, tab_compare, tab_help = st.tabs(
    [
        "0. Mes sites",
        "Datasets",
        "1. Lancer une mission",
        "2. Analyser",
        "3. Comparer",
        "Guide",
    ]
)

# ════════════════════════════════════════════════════════
# TAB 0 — Your sites / targets
# ════════════════════════════════════════════════════════
with tab_sites:
    st.subheader("Enregistrer vos sites / serveurs")
    st.info(
        "Ce projet **ne scanne pas** votre site en live (contrainte du cours: journaux synthétiques). "
        "Vous ajoutez vos domaines ici comme **actifs cibles**; ensuite l'onglet *Lancer* génère "
        "des alertes fictives **dirigées contre ces actifs** pour que les agents les trient."
    )

    with st.form("add_site_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            hostname = st.text_input(
                "Domaine ou hostname *",
                placeholder="ex: boutique.mondomaine.com",
            )
            name = st.text_input("Nom affiché (optionnel)", placeholder="Boutique prod")
            url = st.text_input("URL (optionnel)", placeholder="https://boutique.mondomaine.com")
        with c2:
            site_type = st.selectbox(
                "Type",
                [
                    "web_server",
                    "api",
                    "database",
                    "mail",
                    "vpn_gateway",
                    "workstation",
                    "other",
                ],
            )
            criticality = st.slider("Criticité métier (1=faible, 5=critique)", 1, 5, 4)
            owner = st.text_input("Propriétaire / équipe", value="Moi")
            zone = st.selectbox("Zone", ["dmz", "internal", "edge", "restricted", "cloud"])
        submitted = st.form_submit_button("Ajouter ce site", type="primary")

    if submitted:
        try:
            row = add_user_site(
                hostname=hostname,
                name=name or None,
                site_type=site_type,
                criticality=criticality,
                owner=owner,
                zone=zone,
                url=url,
            )
            st.success(f"Ajouté: **{row['hostname']}** → id `{row['asset_id']}`")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    user_sites = load_user_sites()
    st.markdown("### Vos sites")
    if not user_sites:
        st.write("Aucun site personnel encore — ajoutez-en un ci-dessus.")
    else:
        st.dataframe(user_sites, width="stretch")
        del_id = st.selectbox(
            "Supprimer un site",
            [""] + [s["asset_id"] for s in user_sites],
            format_func=lambda x: "—" if x == "" else next(
                f"{s.get('name', s['hostname'])} ({s['asset_id']})"
                for s in user_sites
                if s["asset_id"] == x
            ),
        )
        if del_id and st.button("Supprimer"):
            delete_user_site(del_id)
            st.rerun()

    st.markdown("### Inventaire complet (lab démo + vos sites)")
    st.dataframe(load_full_inventory(), width="stretch")

# ════════════════════════════════════════════════════════
# TAB — Datasets
# ════════════════════════════════════════════════════════
with tab_data:
    st.subheader("Jeux de données compatibles")
    st.caption(
        "Tous les datasets listés passent le validateur (champs requis + "
        "`dst_asset` présent dans l'inventaire). Ils branchent directement "
        "sur `parse_alert_log` → inventaire → `score_risk_rules` → agents."
    )

    datasets = list_datasets()
    if not datasets:
        st.warning("Aucun dataset trouvé dans data/datasets/")
    else:
        rows = [
            {
                "id": d.get("id"),
                "nom": d.get("name"),
                "alertes": d["validation"]["alert_count"],
                "compatible": "✅" if d["compatible"] else "❌",
                "assets dédiés": "oui" if d.get("has_custom_assets") else "lab ACME",
                "tags": ", ".join(d.get("tags") or []),
                "source": d.get("source") or ("import" if d.get("imported") else "bundled"),
            }
            for d in datasets
        ]
        st.dataframe(rows, width="stretch")

        compatible = [d for d in datasets if d["compatible"]]
        pick = st.selectbox(
            "Prévisualiser / préparer un dataset",
            compatible,
            format_func=lambda d: f"{d.get('name')} ({d.get('id')})",
            key="dataset_preview",
        )
        if pick:
            st.write(pick.get("description") or "")
            st.write(f"**Mission:** {pick.get('mission')}")
            if st.button("Utiliser ce dataset au lancement", type="primary"):
                st.session_state.selected_dataset = pick["id"]
                st.success(
                    f"Dataset **{pick['name']}** sélectionné — "
                    "allez dans l'onglet **Lancer** → mode Dataset."
                )

    st.divider()
    st.subheader("Importer un dataset")
    st.markdown(
        "Formats acceptés: **alerts.json** seul (actifs lab), "
        "**alerts.json + assets.json**, ou **ZIP** du dossier dataset."
    )
    with st.expander("Schéma attendu (copie)"):
        st.json(schema_example())

    up_alerts = st.file_uploader("alerts.json", type=["json"], key="up_alerts")
    up_assets = st.file_uploader("assets.json (optionnel)", type=["json"], key="up_assets")
    up_zip = st.file_uploader("ou dataset.zip", type=["zip"], key="up_zip")
    import_name = st.text_input("Nom du dataset importé", value="Mon import SOC")

    if st.button("Valider & importer"):
        if up_zip is not None:
            result = import_dataset_zip(up_zip.getvalue(), fallback_name=import_name)
        elif up_alerts is not None:
            result = import_alerts_json(
                up_alerts.getvalue(),
                name=import_name,
                assets_raw=up_assets.getvalue() if up_assets else None,
            )
        else:
            result = {"ok": False, "validation": {"errors": ["Fournissez un JSON ou un ZIP"]}}

        if result.get("ok"):
            st.success(f"Import OK → id `{result['dataset_id']}`")
            st.session_state.selected_dataset = result["dataset_id"]
            st.json(result["validation"])
            st.rerun()
        else:
            st.error("Dataset incompatible — corrigez les erreurs ci-dessous")
            st.json(result.get("validation") or result)

# ════════════════════════════════════════════════════════
# TAB 1 — Launch + live
# ════════════════════════════════════════════════════════
with tab_launch:
    st.subheader("Choisir une mission SOC")

    mission_mode = st.radio(
        "Type de mission",
        [
            "Dataset (recommandé)",
            "Scénario démo (ACME-LAB)",
            "Mes sites (cibles personnalisées)",
        ],
        horizontal=True,
    )

    left, right = st.columns([1, 1])
    custom_targets: list[str] = []
    scenario = list(config.SCENARIOS.keys())[0]
    selected_ds = st.session_state.get("selected_dataset")
    pattern = ("web_probe", "Sondes web")

    with left:
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
                if meta["compatible"]:
                    st.success("Compatible avec le pipeline (validé)")
                else:
                    st.error("Incompatible")
                st.write(meta.get("description") or "")
                st.write(meta.get("mission") or "")
        elif mission_mode.startswith("Scénario"):
            scenario_keys = list(config.SCENARIOS.keys())
            labels = {k: config.SCENARIOS[k]["label"] for k in scenario_keys}
            scenario = st.selectbox(
                "Scénario",
                scenario_keys,
                format_func=lambda k: labels[k],
                key="launch_scenario",
            )
            st.write(config.SCENARIOS[scenario]["mission"])
        else:
            inventory = load_full_inventory()
            user_only = [a for a in inventory if a.get("source") == "user"]
            choices = user_only or inventory
            if not user_only:
                st.warning(
                    "Vous n'avez pas encore de site personnel. "
                    "Ajoutez-en un dans **0. Mes sites**, ou sélectionnez des actifs lab ci-dessous."
                )
            options = {a["asset_id"]: a for a in choices}
            custom_targets = st.multiselect(
                "Cibles à inclure dans la mission",
                options=list(options.keys()),
                default=list(options.keys())[: min(3, len(options))],
                format_func=lambda aid: (
                    f"{options[aid].get('name') or options[aid]['hostname']} "
                    f"(crit. {options[aid]['criticality']})"
                ),
            )
            pattern = st.selectbox(
                "Type d'alertes synthétiques à simuler",
                [
                    ("web_probe", "Sondes web / WAF / webshell"),
                    ("bruteforce", "Brute-force / auth"),
                    ("exfil", "Exfiltration / DLP"),
                ],
                format_func=lambda x: x[1],
            )
            st.caption(
                "Les alertes sont **fabriquées** pour viser vos hostnames — "
                "idéal pour la démo de triage, pas un pentest réel."
            )

        mode = st.radio(
            "Mode d'exécution",
            ["LLM local (réel)", "Rapide (outils + synthèse)"],
            horizontal=True,
            help="LLM local = qualité démo réelle. Rapide = même pipeline, sans attendre le modèle.",
        )
        use_offline = mode.startswith("Rapide") or not ready
        start = st.button("Démarrer le triage", type="primary", use_container_width=True)

    with right:
        st.markdown("**Chaîne des agents**")
        st.markdown(
            "Coordonnateur → Collecteur → Classificateur → "
            "Corrélateur → Évaluateur → Rapporteur"
        )
        st.markdown(
            "**Outils utilisés:** `parse_alert_log`, "
            "`lookup_asset_inventory`, `score_risk_rules`"
        )
        if mission_mode.startswith("Mes") and custom_targets:
            st.markdown("**Cibles sélectionnées:**")
            inv = {a["asset_id"]: a for a in load_full_inventory()}
            for tid in custom_targets:
                a = inv.get(tid, {})
                st.write(f"- `{a.get('hostname', tid)}` ({a.get('type', '?')})")
        if mission_mode.startswith("Dataset") and selected_ds:
            st.markdown(f"**Dataset actif:** `{selected_ds}`")

    progress_bar = st.progress(0, text="En attente…")
    status_line = st.empty()
    checklist_box = st.empty()
    graph_box = st.empty()
    output_box = st.empty()

    if start:
        st.session_state.live_log = []
        crew = SOCObservatoryCrew(store=store)

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
            st.balloons()
            st.markdown("### Brief final")
            st.write(result.get("final_result") or "")
            st.info("Passez à l'onglet **Analyser une exécution** — cette run est présélectionnée.")

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
        st.warning("Aucune exécution. Lancez une mission dans l'onglet 1.")
    else:
        st.subheader("Choisir une exécution à rejouer")
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

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Scénario", run_meta.get("scenario_label") or "—")
        m2.metric("Statut", run_meta.get("status") or "—")
        m3.metric("Qualité", run_meta.get("quality_score") or 0)
        m4.metric("Durée (s)", round(float(run_meta.get("total_duration_s") or 0), 1))

        max_step = max(int(run_steps["step_index"].max()) if not run_steps.empty else 0, 0)
        if max_step > 0:
            replay_idx = st.slider(
                "Relecture étape par étape (faites glisser pour voir chaque agent)",
                0,
                max_step,
                0,
            )
        else:
            replay_idx = 0
            st.caption("Cette exécution n'a qu'une seule étape — relecture indisponible.")

        active = None
        if not run_steps.empty:
            match = run_steps.loc[run_steps["step_index"] == replay_idx, "agent"]
            active = match.iloc[0] if len(match) else None

        st.markdown("**Qui travaille à cette étape ?** (orange = actif)")
        chart(fig_agent_graph(active_agent=active), key="analyze_graph")
        agent_checklist(
            [a for a in AGENT_ORDER if not run_steps.empty and a in set(run_steps.loc[run_steps["step_index"] <= replay_idx, "agent"])],
            active,
        )

        c1, c2 = st.columns(2)
        with c1:
            chart(fig_timeline(run_steps), key="analyze_timeline")
            st.caption("Barres = temps passé par agent sur cette mission.")
        with c2:
            chart(fig_sankey(run_steps), key="analyze_sankey")
            st.caption("Épaisseur = volume de jetons / messages transmis.")

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

    st.sidebar.header("Filtres (onglet Comparer)")
    if st.sidebar.button("Actualiser"):
        st.rerun()

    scenario_opts = sorted(runs["scenario"].unique()) if not runs.empty else []
    status_opts = sorted(runs["status"].unique()) if not runs.empty else []
    sel_scenarios = st.sidebar.multiselect(
        "Scénarios", scenario_opts, default=scenario_opts, key="flt_sc"
    )
    sel_status = st.sidebar.multiselect(
        "États", status_opts, default=status_opts, key="flt_st"
    )
    sel_agents = st.sidebar.multiselect(
        "Agents", AGENT_ORDER, default=AGENT_ORDER, key="flt_ag"
    )

    runs_f = filter_runs(runs, scenarios=sel_scenarios or None, statuses=sel_status or None)
    run_id_set = set(runs_f["run_id"]) if not runs_f.empty else set()
    steps_f = steps[steps["run_id"].isin(run_id_set)] if not steps.empty else steps
    if sel_agents and not steps_f.empty:
        steps_f = steps_f[steps_f["agent"].isin(sel_agents)]

    kpis = kpi_dict(runs_f, steps_f)
    st.subheader("Tableau de bord global")
    a, b, c, d = st.columns(4)
    a.metric("Exécutions", kpis["n_runs"])
    b.metric("Réussite", f"{kpis['success_rate']} %")
    c.metric("Durée moy.", f"{kpis['avg_duration']} s")
    d.metric("Jetons", f"{kpis['total_tokens']:,}")
    e, f, g, h = st.columns(4)
    e.metric("Coût USD", kpis["total_cost"])
    f.metric("Erreurs", kpis["errors"])
    g.metric("Agent fréquent", kpis["most_used_agent"])
    h.metric("Plus lent", kpis["slowest_agent"])
    st.caption(
        "Ces chiffres se mettent à jour quand vous lancez de nouvelles missions "
        "ou changez les filtres à gauche."
    )

    if runs_f.empty:
        st.info("Aucune donnée pour ces filtres.")
    else:
        metric = st.selectbox(
            "Comparer les agents sur…",
            ["duration_s", "tokens", "quality_score", "cost_usd", "errors"],
            format_func=lambda x: {
                "duration_s": "Durée moyenne",
                "tokens": "Jetons",
                "quality_score": "Qualité",
                "cost_usd": "Coût",
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

        st.markdown("#### Deux exécutions côte à côte")
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

        st.subheader("Réponses aux questions d'analyse")
        for bullet in interpretation_bullets(runs_f, steps_f):
            st.markdown(f"- {bullet}")

# ════════════════════════════════════════════════════════
# TAB 4 — Viz guide
# ════════════════════════════════════════════════════════
with tab_help:
    st.markdown(
        """
### À quoi sert chaque visualisation ?

| Graphique | Question à laquelle il répond |
|---|---|
| **Graphe des agents** | Qui parle à qui ? Qui est actif maintenant ? |
| **Timeline** | Dans quel ordre et combien de temps chaque étape ? |
| **Sankey** | Où circulent les jetons / messages ? |
| **Barres comparatives** | Quel agent coûte le plus (temps, jetons, erreurs) ? |
| **Heatmap** | Quel couple scénario×agent est un goulot ? |
| **KPI** | Santé globale du système en un coup d'œil |

### Priorités P1 / P2 / P3
Calculées par l'outil `score_risk_rules` (gravité × criticité d'actif), puis confirmées par l'évaluateur et résumées par le rapporteur.
        """
    )

st.divider()
st.caption(
    "Données synthétiques ACME-LAB · traces SQLite · modèle local Heretic Cerebellum · "
    "aucune donnée personnelle."
)
