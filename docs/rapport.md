# Rapport — Observatoire multiagents SOC (A5)

## 1. Problème

Les équipes TI reçoivent un volume élevé d’alertes et doivent décider rapidement lesquelles exigent une intervention. Un chatbot unique peinerait à combiner collecte, classification, corrélation, scoring et rédaction. Ce projet construit un **système multiagents** de triage et un **observatoire** pour mesurer coût, durée, qualité et goulots.

**Client potentiel :** PME, MSSP, collèges — abonnement par actifs surveillés.  
**Données :** journaux **synthétiques** ACME-LAB uniquement.

## 2. Agents

| Agent | Rôle | Interaction |
|---|---|---|
| Coordonnateur | Décompose la mission | → Collecteur |
| Collecteur | Charge alertes + inventaire | outils → Classificateur |
| Classificateur | Type / gravité / FP | → Corrélateur |
| Corrélateur | Campagnes / chaînes | → Évaluateur |
| Évaluateur | Vérifie + score risque | outil règles → Rapporteur |
| Rapporteur | Brief P1/P2/P3 | sortie finale |

## 3. Architecture

- Orchestration : **CrewAI** (processus séquentiel)  
- LLM : **llama-server** + GGUF local Heretic Cerebellum  
- Observabilité maison : traces SQLite (équivalent pédagogique à AgentOps)  
- UI : **Streamlit** + **Plotly**

## 4. Données

Cinq scénarios × ≥4 exécutions (≥20 au total) :

1. Brute-force SSH  
2. Hameçonnage / identifiants  
3. Précurseurs ransomware  
4. Déferlement faux positifs IDS  
5. Exfiltration suspecte  

Chaque étape journalise : agent, tâche, état, modèle, horodatages, durée, jetons, coût, outils, retries, erreurs, score qualité.

## 5. Choix de visualisation

| Viz | Pourquoi |
|---|---|
| KPI | Lecture immédiate de santé du système |
| Graphe agents | Relations et agent actif (relecture) |
| Timeline | Ordre et durée des étapes |
| Sankey | Circulation des jetons/messages |
| Barres comparatives | Coût / durée / jetons / qualité |
| Heatmap | Latence ou erreurs scénario × agent |

## 6. Interprétation (appuyée sur les traces)

Mesures sur le jeu collecté (**21 exécutions**, 5 scénarios, 100 % succès) :

- **Jetons totaux** ≈ 62 700 ; **durée moyenne** ≈ 20,5 s (live LLM ~60–75 s, offline outils+synthèse ≪ 1 s).  
- **Agent le plus lent** : `evaluateur` (prompts de vérification + scores règles).  
- **Agent le plus fréquent** dans les étapes : chaque run appelle les 6 agents ; le volume d’étapes est homogène.  
- Les **outils** (parse, inventaire, règles) sont quasi instantanés ; la latence live vient des **appels LLM**.  
- **noisy_ids** : le rapporteur isole correctement le signal (webshell) du bruit SQLi scanner.  
- **bruteforce_ssh** / **ransomware** / **exfiltration** : plus de priorités P1 liées à la criticité des actifs.  
- Coût API = **0 $** (GGUF local) ; le coût réel se lit en **secondes GPU** et jetons.  
- Corrélation coût↔qualité peu informative à coût nul ; la qualité suit surtout la complétude du brief.

## 7. Limites

- Modèle local 35B-A3B sur 12 Go VRAM : offload partiel, débit variable.  
- Flux séquentiel (pas de parallélisme multi-agents).  
- Scores de qualité heuristiques (longueur + présence de priorités).  
- Données synthétiques : pas de validation sur SOC réel.

## 8. Recommandations (≥3)

1. **Réduire max_tokens** et garder `enable_thinking=false` pour baisser latence/jetons.  
2. **Pré-filtrer** les alertes info/low dans `score_risk_rules` avant les agents LLM.  
3. **Paralléliser** classification d’alertes indépendantes après la collecte.  
4. Ajouter une boucle de **re-vérification** uniquement si l’évaluateur signale une incohérence (évite communications inutiles).

## 9. Conclusion

L’observatoire montre *ce que font les agents*, *comment ils performent*, et *où intervenir* (prompts, règles, parallélisation). Le prototype est démontrable localement, sans données sensibles, et aligné sur la grille du cours 420-VD2-ID.
