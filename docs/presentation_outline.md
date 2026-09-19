# Plan de présentation (10–12 minutes)

## Timing

| Min | Contenu | Qui |
|---|---|---|
| 0–1 | Problème SOC / sujet A5 commercial | Équipe |
| 1–3 | Les 6 agents + 3 outils | Membre A |
| 3–6 | Démo live : `run_scenario` ou relecture dashboard | Membre B |
| 6–9 | Parcourir KPI, graphe, Sankey, heatmap | Membre A |
| 9–11 | Interprétation + 3 recommandations | Membre B |
| 11–12 | Limites, questions | Équipe |

## Démo checklist

1. `bash scripts/start_llm.sh` (déjà démarré si possible)  
2. `streamlit run dashboard/app.py`  
3. Filtrer un scénario ransomware → montrer P1  
4. Slider de relecture → nœud actif sur le graphe  
5. Comparer deux runs  

## Points à savoir expliquer

- Pourquoi CrewAI séquentiel  
- Comment les traces sont écrites (SQLite)  
- Différence outils déterministes vs LLM  
- Pourquoi données synthétiques (éthique / course)
