# Onyx Integration Guide (PilotSuite Styx)

## Zielbild

Onyx passt sehr gut zu Styx, aber als **Ergaenzung**, nicht als Ersatz:

- **Styx (Core + HA Integration)** bleibt dein Home-Automation Control-Plane
  mit Event-Pipeline, Habitus, Mood, Graph, sicheren Aktionen und HA-UI.
- **Onyx** wird dein Knowledge-Plane fuer Dokumente, Connectoren und Team-Chat.

Kurz: **Styx steuert das Zuhause, Onyx erschliesst Wissen**.

## Empfohlene Topologie

1. Onyx als Chat- und RAG-Oberflaeche betreiben.
2. In Onyx LLM-Provider konfigurieren:
   - lokal: Ollama
   - oder cloud: Ollama Cloud/OpenAI-kompatibel
3. Styx als Action-Layer anbinden:
   - **OpenAPI Actions** mit `docs/integrations/onyx_styx_actions.openapi.yaml`
   - optional **MCP Server** ueber `POST /mcp`

## Warum diese Aufteilung

- Onyx bringt starke Connector-/RAG-Funktionen (Drive, Slack, Mail, etc.).
- Styx bringt domain-spezifische Smart-Home-Intelligenz und sichere Aktionspfade.
- So vermeidest du, dass Onyx direkt an HA intern „vorbei“ steuert.

## Sicherheitsregeln (wichtig)

- Verwende einen dedizierten Styx-Token fuer Onyx.
- Starte mit read-only + klar begrenzten Action-Endpunkten.
- Lege in Onyx Agent-Instruktionen fest: keine unbestaetigten riskanten Aktionen.

## RAG-Strategie ohne Doppelchaos

- **Onyx indexiert externe Wissensquellen** (Dokumente, Apps, Unternehmenswissen).
- **Styx haelt Smart-Home-Gedaechtnis** (Events, Patterns, Habitus, Mood-Kontext).
- Nutze Onyx fuer Recherche/Erklaerung und Styx fuer Ausfuehrung im Zuhause.

## Technischer Contract

- Chat API: `/v1/chat/completions`
- Modelle: `/v1/models`
- MCP: `/mcp`
- Action-Subset (OpenAPI): `docs/integrations/onyx_styx_actions.openapi.yaml`

Wenn du Onyx als primaeren Chat nutzt, sollte HA Assist trotzdem auf Styx bleiben,
damit lokale Latenz, Token-Fluss und Automationskontext stabil bleiben.
