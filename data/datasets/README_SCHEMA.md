# Format dataset compatible Observatoire SOC

Chaque dossier sous `data/datasets/<id>/` contient:

- `manifest.json` — métadonnées + mission
- `alerts.json` — liste d'alertes (obligatoire)
- `assets.json` — inventaire optionnel (sinon ACME-LAB par défaut)

## Champs alerte requis
alert_id, ts, source, rule, severity, dst_asset, msg

severity ∈ critical|high|medium|low|info|unknown

`dst_asset` doit exister dans `assets.json` **ou** dans l'inventaire lab
(SRV-DC01, SRV-WEB01, SRV-FILE02, SRV-BACKUP, SRV-DB01, SRV-MAIL01, VPN-GW01, WS-FIN-12, WS-HR-03, IOT-CAM07).

## Import UI
Onglet Datasets: upload `alerts.json` (+ assets optionnel) ou ZIP du dossier dataset.
