# PilotSuite Setup Guide

Stand: **v8.11.0**

Diese Datei ist die kompakte Referenz. Die vollständige Anleitung liegt in `SETUP.md`.

## Mindestvoraussetzungen

- Home Assistant `2024.1+`
- PilotSuite Core Add-on erreichbar auf Port `8909`
- HACS für die Integrations-Installation

## Setup in 5 Schritten

1. Core installieren und starten (`pilotsuite-styx-core`)
2. HACS-Integration installieren (`pilotsuite-styx-ha`)
3. HA neustarten
4. Integration **PilotSuite - Styx** hinzufügen
5. In Sprachassistenten **PilotSuite** als Conversation-Agent setzen

## Empfehlung LLM

- Lokal (Default): `qwen3:0.6b`
- Cloud-Fallback: `qwen3.5:cloud` über `https://ollama.com/v1`

## Diagnose

```bash
curl -sS http://<HA-IP>:8909/health
curl -sS http://<HA-IP>:8909/chat/status
```

Wenn HACS `Restart required` anzeigt, ist ein HA-Neustart erforderlich.
