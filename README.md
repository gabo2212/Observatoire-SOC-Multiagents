# Observatoire SOC — Triage multiagents d'alertes (A5)

Tableau de bord interactif + système multiagents pour **trier et prioriser des alertes de cybersécurité** à partir de **journaux 100 % synthétiques** (ACME-LAB).

Cours : **420-VD2-ID** — Visualisation et interprétation des données 2  
Stack : **CrewAI · Flask · Streamlit · Plotly · llama-server (GGUF local)**  
Modèle : `Qwen3.6-35B-A3B-Heretic-Cerebellum-v1-Q3_K_M.gguf`

## Architecture

Six agents en pipeline séquentiel :

1. **Coordonnateur** — décompose la mission  
2. **Collecteur** — charge alertes + inventaire (outils)  
3. **Classificateur** — type / gravité / faux positifs  
4. **Corrélateur** — campagnes et chaînes d'attaque  
5. **Évaluateur** — score de risque + vérification  
6. **Rapporteur** — brief final P1/P2/P3  

Outils (≥2) :

- `parse_alert_log`  
- `lookup_asset_inventory`  
- `score_risk_rules`  

Traces structurées → SQLite `data/traces/observatory.db`, écrites uniquement par l'API Flask. Streamlit et les scripts CLI parlent à `http://127.0.0.1:5000`.

## Prérequis

- Linux ou macOS (GPU NVIDIA recommandée sur Linux ; testé RTX 4080 12 Go)  
- Python **3.12** (`uv` ou pyenv)  
- `curl` + accès réseau (Hugging Face + GitHub releases)  
- ~12 Go disque pour le GGUF  

`llama-server` est installé automatiquement dans `./bin` par le script d’installation (sinon fournir un binaire dans le PATH).

## Installation (clone → LLM prêt)

Après `git clone`, une seule commande installe le venv Python, crée `.env`, télécharge le GGUF et place `llama-server` dans `./bin` :

```bash
cd Observatoire-SOC-Multiagents
bash scripts/setup.sh
source .venv/bin/activate
```

Options utiles :

```bash
SKIP_MODEL=1 bash scripts/setup.sh   # deps + llama-server seulement
SKIP_LLAMA=1 bash scripts/setup.sh   # deps + modèle seulement
FORCE_LLAMA=1 bash scripts/setup.sh  # re-télécharger llama-server
```

Étapes manuelles (équivalent) :

```bash
uv venv --python python3.12 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
bash scripts/install_llama_server.sh
bash scripts/download_model.sh
```

## Démarrer le LLM local

```bash
bash scripts/start_llm.sh
# API OpenAI-compatible : http://127.0.0.1:8080/v1
```

Sur 12 Go VRAM, ajuster `N_GPU_LAYERS` dans `.env` (25–35).

## Démarrer l'API

L'API Flask est le seul processus qui écrit SQLite, le statut live, les sites et les datasets. Démarrez-la avant le tableau de bord et avant les scripts.

```bash
source .venv/bin/activate
python -m backend.app
# http://127.0.0.1:5000
```

## Collecter des traces (≥20 exécutions / 5 scénarios)

L'API doit tourner. Les scripts lancent chaque mission par HTTP, puis attendent la fin.

```bash
source .venv/bin/activate
# 4 runs × 5 scénarios = 20 ; 1 live LLM par scénario puis synthèse offline
python -m scripts.run_batch --per-scenario 4 --live 1

# Une mission précise
python -m scripts.run_scenario --scenario ransomware_precursor

# Mode hors-ligne (outils réels + synthèse déterministe)
python -m scripts.run_scenario --scenario bruteforce_ssh --offline
```

Scénarios : `bruteforce_ssh`, `phishing_creds`, `ransomware_precursor`, `noisy_ids`, `exfiltration`.

## Tableau de bord

L'API doit déjà tourner (`python -m backend.app`).

```bash
source .venv/bin/activate
streamlit run dashboard/app.py
```

Fonctions : KPI, graphe multiagents, timeline, Sankey, comparatifs, heatmap, filtres, comparaison de 2 runs, **relecture étape par étape**.

## Structure

```
agents/           # descriptions des rôles
tools/            # parse_alert_log, inventory, risk rules
backend/          # API Flask (seul écrivain) + client HTTP
pipeline/         # CrewAI runner, LLM client, tracing SQLite
dashboard/        # Streamlit + Plotly (client de l'API)
data/alerts/      # journaux synthétiques (5 scénarios)
data/inventory/   # actifs ACME-LAB
data/traces/      # observatory.db + export JSON
docs/             # rapport + plan de présentation
scripts/          # setup, download_model, install_llama_server, start_llm, run_*
```

## Sécurité / confidentialité

- Aucune clé API cloud requise (LLM local).  
- Ne pas committer `.env` ni les fichiers `.gguf`.  
- Pas de données personnelles : alertes et inventaire fictifs.  
- Pas de demande de « raisonnement interne détaillé » au modèle ; sorties = tâches, outils, résultats.

## Site Vercel (slides + aperçu)

Déploiement statique : page d’accueil + deck HTML.

- **Live** : https://observatoire-soc-static.vercel.app/
- Accueil : `/` (`index.html`)
- Slides : https://observatoire-soc-static.vercel.app/presentation

Le dashboard Streamlit et le LLM local **ne tournent pas** sur Vercel — uniquement en local (GPU).

## Documentation

- [docs/rapport.md](docs/rapport.md) — rapport complet  
- [docs/presentation_outline.md](docs/presentation_outline.md) — démo 10–12 min  
- [docs/checklist.md](docs/checklist.md) — grille / liste de vérification  
- [presentation.html](presentation.html) — deck HTML (8 slides)  
- [docs/tech-stack-report.canvas.tsx](docs/tech-stack-report.canvas.tsx) — pile technique, pipeline et traces (canvas)  
- [docs/api-mvt-setup.canvas.tsx](docs/api-mvt-setup.canvas.tsx) — API Flask, couches modèle / vue / template, et écart avec l’ancien accès direct (canvas)  

## Licence pédagogique

Projet étudiant — données synthétiques uniquement.
