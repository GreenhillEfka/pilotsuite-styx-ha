# Dev Worklog (WIP)

Kurzüberblick über laufende Arbeiten im Branch `dev` (vor dem nächsten Add-on Release).

## Stand
- Letztes Add-on Release (main): `copilot_core-v0.2.4`

## Recent Work (2026-02-09)
- **habitus_dashboard_cards v0.1 kernel**: API endpoint for Lovelace dashboard pattern recommendations
  - Endpoint: `/api/v1/habitus/dashboard_cards` (returns templates for overview, room, energy, sleep patterns)
  - Documentation-first module: provides best practices for core-only cards
  - Capabilities flag added; health check at `/api/v1/habitus/dashboard_cards/health`

## Next
- Event ingest + forwarder contracts schärfen (idempotency keys, minimal schema)
- Brain Graph: echtes Feeding aus Events + SVG Rendering (statt Placeholder)
