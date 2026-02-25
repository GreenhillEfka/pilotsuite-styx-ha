# PilotSuite Styx – Setup (HA + Core)

Stand: **v8.10.0**

## 1) Core Add-on installieren

1. Home Assistant → **Einstellungen** → **Add-ons** → **Add-on Store** → Menü (⋮) → **Repositories**
2. Repo hinzufügen: `https://github.com/GreenhillEfka/pilotsuite-styx-core`
3. **PilotSuite Core** installieren und starten
4. Prüfen: `http://<HA-IP>:8909/health` muss `200 OK` liefern

## 2) HACS Integration installieren

1. HACS → **Integrations** → Menü (⋮) → **Custom repositories**
2. Repo hinzufügen: `https://github.com/GreenhillEfka/pilotsuite-styx-ha` (Typ: `Integration`)
3. **PilotSuite - Styx** installieren
4. Home Assistant neu starten

## 3) Integration einrichten

1. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen** → `PilotSuite - Styx`
2. **Zero Config** nutzen (empfohlen) oder manuell:
   - Host: `192.168.30.18` (oder HA-Host)
   - Port: `8909`
   - Token: identisch zum Core `auth_token` (falls gesetzt)

## 4) Conversation-Agent setzen

1. **Einstellungen** → **Sprachassistenten**
2. Pipeline öffnen
3. Conversation-Agent auf **PilotSuite** setzen

## 5) Modellkonfiguration (Core)

Im Core Add-on (Configuration):
- Lokal: `conversation_ollama_url`, `conversation_ollama_model` (Default: `qwen3:0.6b`)
- Cloud-Fallback: `conversation_cloud_api_url=https://ollama.com/v1`, `conversation_cloud_model=qwen3.5:cloud`, `conversation_cloud_api_key`
- Routing: `conversation_prefer_local=true|false`

## 6) Dashboard-Konzept

- Primär: React-Dashboard über Core-Ingress/Port `8909`
- Legacy YAML Dashboards sind optional (`legacy_yaml_dashboards=true`)
- Habituszonen werden über die Integrations-Optionen verwaltet (kein CSV-Flow)

## 7) Smoke Checks

- `GET /health`
- `GET /chat/status`
- `GET /api/v1/status`
- HA Entity: `binary_sensor.ai_home_copilot_online` = `on`

## Troubleshooting

- **HACS: "Restart required"**: normal nach Install/Update → HA neu starten.
- **Stale Repairs "CoPilot Seed"**: ab `v8.9.1` werden alte Low-Signal-Seed-Issues beim Setup automatisch bereinigt.
- **Core nicht erreichbar**: Host/Port/Token in Integrationsoptionen prüfen.
- **Chat ohne Antwort**: Core-Logs + `/chat/status` prüfen; ggf. Modell im Core anpassen.

## Version-Paarung

- HA Integration: `8.10.0`
- Core Add-on: `8.10.0`

Für Add-on-Info-Screen: siehe `pilotsuite-styx-core/copilot_core/DOCS.md`.
