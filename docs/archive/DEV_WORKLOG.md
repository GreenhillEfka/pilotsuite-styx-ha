# Dev Worklog (WIP)

Kurzüberblick über laufende Arbeiten im Branch `main` (nach dem letzten Release).

## Stand
- Letztes Add-on Release (main): **copilot_core-v0.4.16**
- Alle PROJECT_PLAN Milestones (M0-M3) vollständig implementiert!
- Security Fix v0.4.16: log_fixer_tx API Auth hinzugefügt

## Recent Work (2026-02-15)

### Autopilot Release v0.4.16
- ✅ log_fixer_tx API: `@require_api_key` Decorator auf allen 6 Endpunkten
- ✅ CHANGELOG.md v0.4.16 erstellt
- ✅ INDEX.md aktualisiert mit Security-Hinweis
- ✅ GitHub commits + tag v0.4.16 gepusht

### Habitus Dashboard Cards v0.1 (dev-habitus-dashboard-cards)
- **habitus_dashboard_cards v0.1 kernel**: API endpoint for Lovelace dashboard pattern recommendations
  - Endpoint: `/api/v1/habitus/dashboard_cards` (returns templates for overview, room, energy, sleep patterns)
  - Documentation-first module: provides best practices for core-only cards
  - Capabilities flag added; health check at `/api/v1/habitus/dashboard_cards/health`

## Next (geplant)
- Event ingest + forwarder contracts schärfen (idempotency keys, minimal schema)
- Brain Graph: echtes Feeding aus Events + SVG Rendering (statt Placeholder)
- Interactive Brain Graph Panel (optional)
- Multi-user preference learning
- Performance-Optimierung bei großen Event-Mengen

## Erledigt (kürzlich)
- ✅ Path allowlist für log_fixer_tx rename operations (v0.4.16)
- ✅ log_fixer_tx API Authentication (v0.4.16)
- ✅ Habitus Dashboard Cards API (v0.4.16)