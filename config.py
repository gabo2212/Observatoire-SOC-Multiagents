"""Central configuration for the SOC multi-agent observatory."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
ALERTS_DIR = DATA_DIR / "alerts"
INVENTORY_PATH = DATA_DIR / "inventory" / "assets.json"
TRACES_DIR = DATA_DIR / "traces"
TRACES_DB = TRACES_DIR / "observatory.db"
DEMO_TRACES_JSON = TRACES_DIR / "demo_runs.json"

OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:8080/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-local")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3.6-35B-A3B-Heretic-Cerebellum-v1-Q3_K_M")
GGUF_PATH = os.getenv(
    "GGUF_PATH",
    str(ROOT / "models" / "Qwen3.6-35B-A3B-Heretic-Cerebellum-v1-Q3_K_M.gguf"),
)

N_GPU_LAYERS = int(os.getenv("N_GPU_LAYERS", "30"))
CTX_SIZE = int(os.getenv("CTX_SIZE", "8192"))
PORT = int(os.getenv("PORT", "8080"))

COST_PER_1M_INPUT = float(os.getenv("COST_PER_1M_INPUT", "0.0"))
COST_PER_1M_OUTPUT = float(os.getenv("COST_PER_1M_OUTPUT", "0.0"))

# Display name for charts / rapport
PROJECT_TITLE = "Observatoire SOC — Triage multiagents d'alertes"
MODEL_DISPLAY = "Qwen3.6-35B-A3B-Heretic-Cerebellum (local GGUF)"

SCENARIOS = {
    "bruteforce_ssh": {
        "label": "Campagne brute-force SSH",
        "mission": (
            "Trier et prioriser les alertes liées à une campagne de brute-force SSH "
            "sur le périmètre synthétique ACME-LAB. Identifier les actifs critiques "
            "touchés, corréler les événements et produire un rapport de triage."
        ),
        "alert_file": "bruteforce_ssh.json",
    },
    "phishing_creds": {
        "label": "Hameçonnage / vol d'identifiants",
        "mission": (
            "Analyser un lot d'alertes d'hameçonnage et de connexions anormales. "
            "Déterminer le risque réel, les faux positifs et les actions prioritaires."
        ),
        "alert_file": "phishing_creds.json",
    },
    "ransomware_precursor": {
        "label": "Précurseurs ransomware",
        "mission": (
            "Évaluer des alertes de mouvement latéral, désactivation de sauvegardes "
            "et chiffrement suspect. Prioriser une réponse avant impact métier."
        ),
        "alert_file": "ransomware_precursor.json",
    },
    "noisy_ids": {
        "label": "Déferlement de faux positifs IDS",
        "mission": (
            "Un IDS bruyant génère des centaines d'alertes. Distinguer le signal "
            "du bruit, estimer le taux de faux positifs et recommander un réglage."
        ),
        "alert_file": "noisy_ids.json",
    },
    "exfiltration": {
        "label": "Exfiltration de données suspecte",
        "mission": (
            "Corréler des transferts volumineux, des accès hors horaires et des "
            "anomalies DLP. Estimer le risque d'exfiltration et la criticité."
        ),
        "alert_file": "exfiltration.json",
    },
}

AGENT_ROLES = {
    "coordinateur": {
        "role": "Coordonnateur SOC",
        "goal": "Décomposer la mission de triage et orchestrer les autres agents",
        "color": "#2563eb",
    },
    "collecteur": {
        "role": "Collecteur d'alertes",
        "goal": "Rassembler et normaliser les alertes et le contexte des actifs",
        "color": "#0891b2",
    },
    "classificateur": {
        "role": "Classificateur",
        "goal": "Classer les alertes par type, gravité et fiabilité",
        "color": "#7c3aed",
    },
    "correlateur": {
        "role": "Corrélateur",
        "goal": "Relier les alertes en campagnes et détecter les motifs",
        "color": "#c2410c",
    },
    "evaluateur": {
        "role": "Évaluateur de risque",
        "goal": "Scorer le risque métier et vérifier la cohérence du triage",
        "color": "#b91c1c",
    },
    "rapporteur": {
        "role": "Rapporteur",
        "goal": "Rédiger le rapport final de priorisation pour l'analyste SOC",
        "color": "#047857",
    },
}