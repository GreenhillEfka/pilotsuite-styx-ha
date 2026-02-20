# Code Review – HA Integration (ai_home_copilot)

Stand: 2026-02-17

## Überblick
Der Review fokussiert auf Code-Qualität/Architektur, Security, Performance, Error Handling und Best Practices. Der Code ist umfangreich; geprüft wurden Kernpfade, Konfiguration, API-Clients, Coordinator/Module, Webhook, Snapshot/Storage und ausgewählte Services.

Geprüfte Schwerpunkte (Auswahl):
- `custom_components/ai_home_copilot/__init__.py`
- `custom_components/ai_home_copilot/config_flow.py`
- `custom_components/ai_home_copilot/config_helpers.py`
- `custom_components/ai_home_copilot/config_options_flow.py`
- `custom_components/ai_home_copilot/config_snapshot.py`
- `custom_components/ai_home_copilot/coordinator.py`
- `custom_components/ai_home_copilot/webhook.py`
- `custom_components/ai_home_copilot/energy_context.py`
- `custom_components/ai_home_copilot/weather_context.py`
- `custom_components/ai_home_copilot/unifi_context.py`
- `custom_components/ai_home_copilot/brain_graph_sync.py`
- `custom_components/ai_home_copilot/core/runtime.py`
- `custom_components/ai_home_copilot/core/module.py`
- `custom_components/ai_home_copilot/core/modules/events_forwarder.py`
- `custom_components/ai_home_copilot/vector_client.py`
- `custom_components/ai_home_copilot/storage.py`

## Zusammenfassung
- P0: keine gefunden.
- P1: 3 (funktionale Fehler und Memory-Leak/Reload-Probleme).
- P2: 6 (Security-Härtung, Timeouts, Input-Validation, Robustheit).
- P3: 3 (Best-Practice/Qualität).

## Findings & Empfehlungen

### P1 (Hoch)
1) **Config-Snapshot bricht zur Laufzeit (NameError)**
Befund: In `custom_components/ai_home_copilot/config_snapshot.py` werden `async_get_zones` und `async_set_zones_from_raw` verwendet, die nicht importiert sind (v2-Funktionen heißen `async_get_zones_v2` und `async_set_zones_v2_from_raw`). Das führt zu einem sofortigen Fehler beim Generieren oder Importieren von Snapshots.
Empfehlung: Auf v2-Funktionen umstellen und Imports/Callsites konsistent machen.

2) **Event-Listener-Leak in BrainGraphSync**
Befund: `custom_components/ai_home_copilot/brain_graph_sync.py` registriert Event-Listener via `hass.bus.async_listen`, speichert jedoch keine Unsubscribe-Funktionen. `async_stop` entfernt die Listener nicht. Nach Reload entstehen doppelte Event-Verarbeitung und potenziell Speicher-/CPU-Leaks.
Empfehlung: Unsub-Callbacks speichern und in `async_stop` aufrufen; zusätzlich Reload-Tests ergänzen.

3) **Fehlerhafte Host-Normalisierung + erzwungenes HTTP**
Befund: `_get_base_url()` in `custom_components/ai_home_copilot/energy_context.py`, `weather_context.py` und `unifi_context.py` nutzt `str.lstrip("http://").lstrip("https://")`, was keine Prefix-Entfernung ist. Bei Hosts mit `http(s)://` werden führende Zeichen beliebig entfernt (z.B. `https://homeassistant.local` → `omeassistant.local`). Zusätzlich wird immer `http://` verwendet, auch wenn der Nutzer `https://` konfiguriert.
Empfehlung: URL sauber parsen (z.B. `urllib.parse.urlsplit` oder `yarl.URL`), Scheme beibehalten und Standard-Scheme nur dann setzen, wenn keines vorhanden ist.

### P2 (Mittel)
1) **Webhook ohne Token akzeptiert alle Requests**
Befund: `custom_components/ai_home_copilot/webhook.py` erlaubt unbegrenzte Requests, wenn kein Token gesetzt ist. Wenn die Webhook-URL extern bekannt wird, können unautorisierte Push-Events ausgelöst werden.
Empfehlung: Token verpflichtend machen oder wenigstens eine explizite Option `allow_unauthenticated_webhook=false` (Default) einführen. Alternativ: zufälliges Shared-Secret zusätzlich zum Webhook-ID erzwingen.

2) **Fehlende Input-Validation im Setup**
Befund: `custom_components/ai_home_copilot/config_helpers.py` `validate_input` ist leer. Dadurch gibt es keine Erreichbarkeitsprüfung, keine Host/Port-Validierung und keine frühe Fehlererkennung.
Empfehlung: Mindestens Host/Port validieren (kein Leerstring, Port-Range), optional Health-Check gegen Core-API, Fehler als `cannot_connect` zurückgeben.

3) **HTTP-Requests ohne explizite Timeouts**
Befund: In `energy_context.py`, `weather_context.py`, `unifi_context.py` und Teilen von `coordinator.py` werden Requests ohne Timeouts ausgeführt. Das kann Tasks blockieren und die HA-Loop belasten.
Empfehlung: `aiohttp.ClientTimeout` setzen oder `async_timeout` nutzen; Timeouts pro Request konfigurieren.

4) **DataUpdateCoordinator: Exceptions statt UpdateFailed**
Befund: `energy_context.py`, `weather_context.py`, `unifi_context.py` werfen generische `Exception`. Das erschwert konsistentes Fehler-Reporting in HA.
Empfehlung: `UpdateFailed` (from `homeassistant.helpers.update_coordinator`) verwenden und konkrete Statuscodes mappen.

5) **VectorStoreClient: Task-Tracking & Overlap**
Befund: `custom_components/ai_home_copilot/vector_client.py` startet Sync-Tasks per `hass.async_create_task`, speichert aber keinen Task-Handle (`_sync_task` bleibt ungenutzt). Bei Unload werden laufende Tasks nicht abgebrochen. Zusätzlich können periodische Syncs überlappen.
Empfehlung: Task-Handle speichern, Overlap verhindern (Lock/Guard), Task sauber canceln.

6) **Potentiell sensitive State-Attribute werden ungefiltert gesendet**
Befund: `vector_client.py` schickt `state.attributes` nahezu vollständig an den Vector Store. Diese Attribute können PII oder Tokens enthalten (z.B. Kamera-URL/Streams).
Empfehlung: Allowlist für Attribute einführen oder `privacy.redact_text`/Redaktions-Helper verwenden, bevor Daten versendet werden.

### P3 (Niedrig)
1) **Inconsistent Auth Header Usage**
Befund: Teile nutzen `Authorization: Bearer`, andere `X-Auth-Token` (`custom_components/ai_home_copilot/const.py`, `coordinator.py`, `api/__init__.py`). Das ist okay, erhöht aber Integrations-Drift.
Empfehlung: Einheitliche Header-Konvention dokumentieren und wo möglich konsolidieren.

2) **ConfigFlow: Fehlerdetails nur geloggt**
Befund: `config_flow.py` loggt Validierungsfehler, liefert dem Nutzer aber nur `cannot_connect`. Das ist UX-neutral, aber Debugging schwerer.
Empfehlung: Optional spezifischere Fehlercodes oder Debug-Info in `description_placeholders` bei Debug-Level.

3) **Doc/Code Drift in Config Snapshot**
Befund: Kommentare verweisen auf v1-Funktionen, Code importiert v2. Das erhöht Wartungskosten.
Empfehlung: Kommentare/Imports bereinigen und v1-Reste entfernen.

## Security Check (SQLi/XSS/Secrets/Input Validation)
- SQL Injection: keine SQL-Benutzung gefunden.
- XSS: keine direkten HTML/Template-Renders im Backend gefunden; Risiko gering.
- Secrets: gute Redaktions-Utilities vorhanden (`privacy.py`, `diagnostics.py`, `ha_errors_digest.py`). Verbesserungsbedarf: Webhook-Auth erzwingen, VectorStore-Payload redaktion.
- Input Validation: `validate_input` fehlt; Bulk-Editor nutzt `yaml.safe_load` (gut).

## Performance & Memory
- Positiv: Events Forwarder hat Queue-Bounds, Rate-Limits und Persistenz (`custom_components/ai_home_copilot/core/modules/events_forwarder.py`).
- Risiken: fehlende Timeouts bei HTTP, ungekürzte Listener im BrainGraphSync, untracked Tasks im VectorStoreClient.

## Error Handling
- Positiv: Strukturierte Fehler-Helfer in `custom_components/ai_home_copilot/core/error_helpers.py`.
- Verbesserungsbedarf: konsistent `UpdateFailed`, klare Statuscode-Mappings, reauth/invalid token Handling.

## Best Practices
- Nutzt `async_get_clientsession` in mehreren Modulen (gut). VectorStoreClient sollte das bevorzugen oder Connector vom HA-Session übernehmen.
- URL/Host-Parsing zentralisieren (ein Helper in `config_helpers.py` oder `core/runtime.py`).

## Test-Gaps / Vorschläge
1) Reload-Tests für BrainGraphSync (Listener-Aufräumen, keine Duplikate).
2) Snapshot-Import/Export Regression-Test (v2-Zones).
3) HTTP Timeout/Retry Tests für `energy_context`, `weather_context`, `unifi_context`.
4) VectorStoreClient Unload-Test (Task-Cancel + Session-Close).

## Positive Observations
- Privacy-First-Ansatz mit Redaction in mehreren Modulen.
- Events Forwarder mit Idempotenz und Persistenz ist solide.
- Modularisierte Architektur (Runtime/Registry/Module-Interface) erleichtert Erweiterungen.

