# CHANGELOG - PilotSuite HA Integration

## [7.7.24] - 2026-02-22 — DASHBOARD WIRING + V2 CLEANUP + ENTITY MINIMIZATION

### Fixes
- **Dashboard-Wiring automatisiert**
  - neue Wiring-Logik erzeugt eine stabile Include-Datei: `ai_home_copilot/lovelace_pilotsuite_dashboards.yaml`.
  - wenn `configuration.yaml` noch keinen `lovelace:`-Block hat, wird ein minimaler Include-Block automatisch ergänzt.
  - wenn bereits ein `lovelace:`-Block existiert, wird eine klare Merge-Anleitung als Persistent Notification ausgegeben.
- **Habitus-Dashboard v2-Hotfix**
  - Generierung nutzt jetzt konsistent `async_get_zones_v2` (statt Legacy-Referenz).
  - behebt fehlerhafte/ausfallende Habitus-Dashboard-Generierung.
- **Auto-Generierung erweitert**
  - bei Setup werden jetzt **beide** Dashboards erzeugt (PilotSuite + Habitus), nicht nur PilotSuite.
  - bei Habitus-Zonen-Updates werden beide Dashboards automatisch regeneriert (ohne Notification-Spam).
- **Dashboard-Entity-Referenzen aufgeräumt**
  - Dashboard-Generator referenziert nur noch tatsächlich vorhandene Entities.
  - reduziert tote/duplizierte Karteninhalte und verbessert UX bei Core-Profile-Setups.

### Tests
- Neue Tests: `tests/test_dashboard_wiring.py`.
- Lokale Regressionen (gezielt): **21 passed, 1 skipped**.

## [7.7.23] - 2026-02-22 — DEVICE DEDUP CLEANUP HARDENING

### Fixes
- **Legacy-Device Cleanup erweitert**
  - Nach der Device-Konsolidierung werden jetzt verwaiste alte PilotSuite-Devices
    (ohne verknuepfte Entities) automatisch aus der Registry entfernt.
  - reduziert verbleibende "altes Gerät bleibt stehen"-Artefakte nach Migration/Update.
- **Sicherheitsnetz fuer Cleanup**
  - Cleanup ist konservativ: entfernt nur reine `ai_home_copilot`-Devices
    ohne fremde Identifier.
  - Fehler im Cleanup-Pfad beeinflussen Setup nicht (best-effort + debug logging).

## [7.7.22] - 2026-02-22 — RUNTIME RELOAD STABILITY + TOKEN FLOW HARDENING

### Fixes
- **Runtime-Unload robust gemacht**
  - unload-Rueckgaben aus Modulen werden jetzt strikt auf `bool` normalisiert.
  - verhindert `AssertionError` beim Config-Entry-Unload/Reload (`async_unload_entry` muss bool liefern).
- **OptionsFlow Connection-Step stabilisiert**
  - `test_light_entity_id=None` wird sauber behandelt statt als invalides Entity-ID-Format zu scheitern.
  - verhindert Reload-/Save-Fehler in Connection-Updates.
- **Network-Schema toleriert optionales Test-Light**
  - `CONF_TEST_LIGHT` akzeptiert jetzt explizit `None` in Config/Options-Schemata.
- **Pipeline-Health kompatibler mit Core-Varianten**
  - Candidates-Check erkennt jetzt auch Payloads ohne `ok`-Flag korrekt als erfolgreich.
  - Habitus-Health faellt bei 404 auf `/api/v1/habitus/health` zurueck.
  - Capabilities-Check faellt bei 404 auf `/api/v1/agent/status` bzw. `/chat/status` zurueck.
- **Core-v1-Sensor fallback erweitert**
  - bei fehlendem `/api/v1/capabilities` werden kompatible Agent-/Chat-Status-Endpoints probiert, statt pauschal `not_supported`.
- **Lovelace-Resource-Autoregistration kompatibel gemacht**
  - unterstuetzt sowohl dict-basierte als auch objektbasierte Lovelace-Datenstrukturen.
  - behebt Fehler `'LovelaceData' object has no attribute 'get'`.
- **Quick-Search-Services repariert**
  - Service-Schema auf gueltige `vol.Optional`-Definitionen umgestellt.
  - Query-Parameter werden korrekt URL-encodiert.
  - Entity-Registry-Zugriffe nutzen den registrierten Registry-Handle statt nicht-existenter Attribute.

## [7.7.21] - 2026-02-22 — CONNECTION NORMALIZATION + LEGACY CLEANUP

### Fixes
- **Connection-Konfiguration wird beim Setup jetzt kanonisch normalisiert**
  - `host`/`port`/`token` werden aus `entry.data + entry.options` konsistent aufgeloest und in `entry.data` gespiegelt.
  - Legacy-Schluessel (`core_url`, `auth_token`, `access_token`, `api_token`) werden auf den Standardpfad migriert.
  - stabilisiert Token/Host-Persistenz ueber Updates und verhindert Drift zwischen Modulen.
- **Core-Failover haertet Auth-Szenarien**
  - Endpoint-Failover springt nicht mehr bei 401/403 auf alternative Hosts.
  - verhindert Fehlschwenks auf ungeeignete Fallback-Hosts bei Tokenproblemen.
- **Docker-Internal nur noch explizit**
  - `host.docker.internal` wird nicht mehr automatisch in allgemeine Fallback-Listen gemischt.
  - kann weiter gezielt aktiviert werden, wenn wirklich benoetigt.
- **Module auf gemergte Connection-Quelle umgestellt**
  - Brain Graph Sync, HomeKit Bridge/Entities, Lovelace Resource Registration, Core v1 API-Calls und N3-Forwarder-Start verwenden jetzt die normalisierte Connection-Aufloesung.
  - beseitigt veraltete `entry.data`-Lesepfade, die zuvor alte Host/Token-Werte verwendeten.
- **Legacy-Text-Entitaeten werden bereinigt**
  - obsolete CSV-/Testlight-Text-Entitaeten werden beim Setup aus der Entity Registry entfernt.
  - reduziert Entitaetsmuell und verhindert UI-Verwirrung.
- **Main-Device-Konsolidierung erweitert**
  - PilotSuite-bezogene Legacy-Devices werden auf das kanonische Hub-Device zusammengefuehrt.
  - reduziert "neues Geraet pro Update"-Effekte.
- **Dashboard-Generator robuster**
  - zentrale Entities/Buttons werden mit Fallback-Kandidaten aufgeloest (`ai_home_copilot_*` und `pilotsuite_*`), damit generierte YAML-Dashboards trotz umbenannter Entity IDs funktionieren.

### Tests
- Lokale HA-Testsuite: **538 passed, 5 skipped**.
- Neue Regressionen:
  - `tests/test_connection_config_migration.py`
  - erweiterte Assertions in `tests/unit/test_core_endpoint.py`

## [7.7.20] - 2026-02-22 — COMMUNICATION PIPELINE HARDENING + TOKEN COMPAT

### Fixes
- **Core endpoint unification across sensor modules**
  - Sensor-API calls verwenden jetzt zentral die aktive Core-Base-URL (inkl. Coordinator-Failover-Endpoint statt statischem `host:port`).
  - behebt Situationen, in denen Coordinator erreichbar war, einzelne Module/Sensoren aber weiterhin gegen einen toten Endpoint liefen.
- **Auth-Header vereinheitlicht**
  - zentrale Header-Bildung (`Authorization` + `X-Auth-Token`) fuer Sensor-Requests.
  - reduziert 401/leer laufende Sensoren bei gemischten Token-Setups.
- **Legacy-Token-Kompatibilitaet im Coordinator**
  - alte Konfigurationen mit `auth_token` werden beim Start auf `token` normalisiert.
  - verhindert stille Auth-Ausfaelle nach Updates/Migrationen.
- **Legacy-Entity-Unique-IDs migriert**
  - betroffene Sensoren wurden von `host:port`-basierten Unique-IDs auf stabile IDs umgestellt.
  - automatische Migration beim Setup verhindert neue Duplikate bei Host/Port-Wechseln.
- **BaseEntity erweitert**
  - neue gemeinsame Helpers fuer Core-URL und Core-Auth-Header.
  - reduziert Drift zwischen Modulen und stabilisiert die Rueckkanal-Kommunikation.

### Tests
- Lokale HA-Testsuite: **531 passed, 5 skipped**.
- Neue Abdeckung fuer BaseEntity Core-URL/Auth-Helper in `tests/test_device_identity.py`.

## [7.7.19] - 2026-02-22 — FLOW RELIABILITY + HABITUS MULTI-AREA + API HARDENING

### Fixes
- **OptionsFlow speichert jetzt stabil und vollstaendig**
  - Optionen werden nicht mehr als Teilobjekt ueberschrieben, sondern sauber gemerged (`entry.data` + `entry.options` + Updates).
  - behebt Konfig-Verluste zwischen Schritten (Connection/Modules/Neurons).
  - API-Token, Host/Port und Modulkonfiguration bleiben damit ueber Updates/Option-Aenderungen erhalten.
- **Habitus-Zonenflow substanziell repariert**
  - Zone-Form unterstuetzt jetzt **Mehrfach-Raumauswahl** (`area_ids`, multi-select) fuer einen Habitusbereich ueber mehrere Zimmer.
  - Edit-Form kann dieselbe Mehrfach-Raumauswahl anzeigen/bearbeiten.
  - Auto-Suggestions (Motion/Lichter/optional) werden ueber mehrere Bereiche zusammengefuehrt.
  - gewaehlte Bereiche werden in Zone-Metadaten persistiert (`metadata.ha_area_ids`).
- **Tagging-Flow verbessert**
  - `edit_tag` ist jetzt zweistufig mit vorbefuellter Entitaetsliste statt leerem Startwert.
  - verhindert versehentliches Ueberschreiben bestehender Tag-Zuweisungen.
- **API-Erreichbarkeit erweitert**
  - Core-Host-Fallbacks ergaenzt: `homeassistant`, `supervisor`, `host.docker.internal`.
  - robuster bei Container-/Dev-Topologien, in denen `homeassistant.local` nicht aufloest.
- **Token-Header-Konsistenz**
  - betroffene Sensoren nutzten teils nur `auth_token`; jetzt fallback auf `token` + Versand von `Authorization` und `X-Auth-Token`.
  - reduziert 401/leer laufende Sensoren durch inkonsistente Tokenquellen.
- **CSV-Altpfade fuer Entitaetsauswahl weiter bereinigt**
  - veraltete Text-Entities fuer entitaetsbasierte Konfiguration entfernt:
    - `text.ai_home_copilot_seed_sensors_csv`
    - `text.ai_home_copilot_test_light_entity_id`
  - selector-basierte Auswahl im Options-Flow ist jetzt der saubere Standard.

### Versionierung / Historie
- Versions- und Statusdateien auf `7.7.19` synchronisiert.
- Update-Historie fuer diesen Fix-Block konsistent nachgezogen.

### Tests
- Lokale HA-Testsuite: **529 passed, 5 skipped**.
- Neue Tests:
  - `tests/test_config_options_flow_merge.py`
  - erweiterte Assertions in `tests/unit/test_core_endpoint.py`
  - Schema-Regressionen in `tests/test_config_zones_flow.py`

## [7.7.18] - 2026-02-22 — MEDIA PLAYER CONFIG UX CLEANUP

### Fixes
- **CSV-Textfelder fuer Media-Player entfernt**
  - Die veralteten Text-Entities
    - `text.ai_home_copilot_media_music_players_csv`
    - `text.ai_home_copilot_media_tv_players_csv`
    wurden entfernt.
  - Damit bleibt fuer Media-Player-Konfiguration nur noch der selector-basierte Weg ueber
    **Integrations-Optionen → Modules** (Dropdown/EntitySelector, multiple=true).
- Reduziert UI-Verwirrung zwischen altem CSV-Setup und aktuellem dropdown-basiertem Setupflow.

### Tests
- Lokale HA-Testsuite: **527 passed, 5 skipped**.

## [7.7.17] - 2026-02-22 — DASHBOARD AUTO-REFRESH + CORE PROFILE ACCESS

### Fixes
- **PilotSuite Dashboard aktualisiert sich jetzt bei Zonen-Aenderungen automatisch**
  - Bei `Habitus Zones v2` Updates wird `pilotsuite_dashboard_latest.yaml` automatisch neu generiert (debounced).
  - Damit bleiben neu erstellte/geaenderte Zonen ohne manuelles Re-Generate im YAML-Dashboard sichtbar.
- **Core-Entity-Profile hat jetzt ebenfalls PilotSuite-Dashboard-Buttons**
  - Auch im `entity_profile=core` sind jetzt verfuegbar:
    - `button.ai_home_copilot_generate_pilotsuite_dashboard`
    - `button.ai_home_copilot_download_pilotsuite_dashboard`
  - Vorher war das nur im `full`-Profil sichtbar.
- **Sauberes Unload**
  - Auto-Refresh Listener/Timer werden beim Unload sauber entfernt (kein Listener-Leak).

### Tests
- Lokale HA-Testsuite: **527 passed, 5 skipped**.

## [7.7.16] - 2026-02-22 — CONVERSATION ID + DEVICE IDENTITY HARDENING

### Fixes
- **Assist-Chat Pattern-Fehler behoben**
  - `conversation_id` wird jetzt immer auf ein ULID-kompatibles Format normalisiert.
  - Ungueltige/non-ULID IDs werden deterministisch auf eine stabile 26-char ID gemappt.
  - Verhindert Frontend/API-Fehler wie `The string did not match the expected pattern`.
- **Main-Device-Identitaet weiter gehaertet**
  - Legacy Haupt-Identifiers (`ai_home_copilot`, `copilot_hub`, `pilotsuite_hub`) werden jetzt zentral als Alias gefuehrt.
  - Debug-Sensor haengt jetzt am gleichen Hauptgeraet (`PilotSuite - Styx`) statt ein separates Legacy-Geraet zu erzeugen.

### Tests
- Neue/aktualisierte Tests fuer Conversation-ID-Normalisierung und Device-Identity.
- Gesamtsuite lokal: **527 passed, 5 skipped**.

## [7.7.15] - 2026-02-22 — CHAT TIMEOUT HOTFIX

### Fixes
- **Conversation-Timeout deutlich erhoeht**
  - `coordinator.api.async_chat_completions()` nutzt jetzt `90s` statt `20s`.
  - Hintergrund: lokale 4B-Modelle (`qwen3:4b`) brauchen auf HA-Hardware haeufig >20s.
- Verhindert falsche Chat-Fehler durch zu kurze Client-Timeouts direkt nach Modellstart/Warmup.

### Validierung
- Test-Suite unveraendert gruen: **524 passed, 5 skipped**.

## [7.7.14] - 2026-02-22 — SETUP FLOW + ZONE RELIABILITY

### Fixes
- **Keine neuen Doppel-Instanzen mehr beim Neu-Hinzufuegen**
  - Config Flow jetzt als Single-Instance abgesichert (`single_instance_allowed` + stabile `unique_id`).
  - verhindert, dass bei wiederholtem Hinzufuegen neue Entry-/Device-Zweige entstehen.
- **Stabile Device-Identitaet**
  - zentrale Haupt-Device-ID (`styx_hub`) eingefuehrt, legacy `host:port` IDs bleiben als Alias erhalten.
  - reduziert "neues Geraet pro Version"-Effekte bei Updates/Rekonfiguration.
- **Habituszonen-Erstellung repariert**
  - Create-Flow erzeugt keine invalide `HabitusZoneV2(zone_id=\"\")` mehr.
  - Zone-ID wird jetzt automatisch aus Bereich/Name generiert und bei Kollision suffixiert.
- **Asynchrone Bereichs-Suggestions fuer Zonen**
  - optionaler `area_id`-Selector im Zone-Formular.
  - Motion/Lichter werden bei Bedarf automatisch aus dem gewaehlten Bereich vorgeschlagen.
- **Motion-Validierung robuster**
  - deutsche Entitaets-Hinweise (`bewegung`, `praesenz`, `anwesenheit`, `pir`, ...) werden erkannt.
  - explizit als `motion` zugewiesene `binary_sensor`/`sensor` passieren auch ohne saubere `device_class`.

### UX / Setup
- Setup/Options auf selector-basierte Entity-Auswahl erweitert:
  - Media, Seed-Entities, Forwarder-Additional-Entities, Tracked Users, Waste, Birthday, Neurons.
- Zone-Menues (Edit/Delete) nutzen Dropdown-Selector statt freier Texteingabe.
- Wizard-Zonen-Schritt faellt bei leeren Optionen nicht mehr auf Freitext zurueck.

### Zero-Config / Agent-Lifecycle
- Agent Auto-Config kann jetzt Core-Self-Heal aktiv triggern:
  - bei fehlgeschlagenem Connectivity-Check,
  - bei degradiertem Agent-Status,
  - zusaetzlich als verzogerter Post-Setup-Check (60s) fuer lange Modell-Downloads.
- Neuer Service: `ai_home_copilot.repair_agent` fuer manuelles Self-Heal-Triggering aus HA.
- Conversation-Agent nutzt robustes Sprach-Fallback (`user_input.language` -> HA-Default -> `de`).
- Conversation-ID-Normalisierung ist jetzt kompatibler: vorhandene IDs werden beibehalten, statt strikt ersetzt zu werden.

### Tests
- Neue Tests:
  - `tests/test_config_zones_flow.py`
  - `tests/test_config_schema_builders_entities.py`
- Erweiterte Validierungstests fuer Motion-Edgecases in `tests/test_entity_validation.py`.
- Gesamtsuite lokal: **524 passed, 5 skipped**.

## [7.7.13] - 2026-02-22 — STATUS ENTITY + AGENT API COMPAT

### Fixes
- `binary_sensor` Online-Status auf robustes Dict-Reading umgestellt (`coordinator.data["ok"]`) statt Attributzugriff.
  - behebt Laufzeitfehler beim Entity-Setup (`binary_sensor.ai_home_copilot_online`).
- `pipeline_health_entities` auf robustes Dict-Reading umgestellt (`ok`/`version`).
  - behebt wiederholte Update-Fehler durch `coordinator.data.ok` / `.version` Attributzugriff.
- Agent Auto-Config jetzt abwaertskompatibel:
  - primaer `/api/v1/agent/*`
  - Fallback auf `/chat/status`, falls Agent-Endpoints im Core noch nicht vorhanden sind.

### Tests
- Neue Tests fuer Status-Entities mit Dict-basiertem Coordinator-Payload hinzugefuegt.

## [7.7.12] - 2026-02-22 — HASSFEST/HACS CI FIX

### CI-Konformitaet wiederhergestellt
- `manifest.json` fuer `ai_home_copilot` bereinigt:
  - nicht akzeptiertes Feld `homeassistant` entfernt (hassfest Schema-Kompatibilitaet).
- `strings.json` bereinigt:
  - unzulaessigen `_comment`-Key im `settings_legacy`-Step entfernt.

### Wirkung
- HACS/hassfest Validation blockiert Releases nicht mehr durch Schemafehler.
- Integration-Version auf `7.7.12` angehoben.

## [7.7.11] - 2026-02-22 — CONVERSATION ID + TOKEN + ZONE FORM HOTFIX

### Fixes fuer gemeldete Restfehler
- Conversation-Agent erzeugt jetzt strikt ULID-kompatible `conversation_id`-Werte (Crockford Base32, 26 Zeichen).
  - behebt Assist/Frontend-Fehler wie: `The string did not match the expected pattern`.
- Options-Flow (`connection`) behaelt API-Token jetzt robust aus `entry.data` **oder** `entry.options` bei.
  - verhindert Token-Verlust bei leeren Token-Submits und nach Konfig-/Versionszyklen.
- Habitus-Zonen-Form verwendet bei optionalen Single-Entity-Selects kein leeres `\"\"` mehr als Default.
  - vermeidet Pattern-Fehler beim Rendern/Absenden der Zone-Form.
- Device-Info-Naming vereinheitlicht auf `PilotSuite - Styx` fuer neue/aktualisierte Device-Metadaten.

### Tests
- HA Test-Suite: **511 passed, 5 skipped**
- Neue Unit-Tests fuer Conversation-ID-Helper hinzugefuegt.

## [7.7.10] - 2026-02-22 — CHAT + ZONES + ENTITY SURFACE HARDENING

### Chat-/Endpoint-Robustheit
- API-Client akzeptiert nur gueltige JSON-Antworten von Core-Endpunkten; HTML/Fremdantworten triggern jetzt klaren Failover statt stiller Fehldeutung.
- Endpoint-Failover erweitert: bei 4xx/Transportfehlern wird auf alternative Kandidaten gewechselt.
- Port-Fallback auf `8909` zusaetzlich zum konfigurierten Port, um Fehlkonfigurationen (z. B. versehentlich `8123`) automatisch abzufangen.
- Conversation-Agent normalisiert `conversation_id` defensiv auf ein gueltiges, stabiles Format.

### Habitus-Zonen-Flow repariert
- Create/Edit-Form toleriert leere Selector-Eingaben ohne Frontend-Pattern-Blocker und validiert anschliessend serverseitig mit klaren Feldfehlern.
- Persistenz-/Validierungsfehler werden als Formfehler zurueckgespielt statt den Flow hart abbrechen zu lassen.
- Edit-Flow ersetzt bei geaenderter `zone_id` jetzt korrekt die alte Zone (kein versehentliches Duplikat mehr).

### Entity-Flut eingedaemmt (Default)
- Neues Entity-Profil (`core`/`full`) eingefuehrt; Default ist `core`.
- `core` reduziert die standardmaessig erzeugten Sensor-/Button-/Binary-Sensor-Entitaeten auf eine schlanke, produktive Basis.
- Profil ist in Setup und Optionen konfigurierbar.

### Konfigurations-UX
- Connection-Optionsflow normalisiert Host/Port konsistent.
- Discovery/Validation prueft Endpunkte strenger auf echte PilotSuite-Core-API-Antworten.
- Uebersetzungen fuer `connection`/`modules`-Steps und `entity_profile` vervollstaendigt.

## [7.7.9] - 2026-02-22 — BULLETPROOF SETUP FLOW PATCH

### Kritischer Setup-Fix (Root Cause)
- Coordinator nutzt jetzt denselben API-Client-Vertrag wie andere Module (Shared API Client als Basisklasse).
- Dadurch sind `async_get/async_post/async_put` sowie `get_with_auth/post_with_auth/put_with_auth` auf `coordinator.api` verlässlich verfügbar.
- Das verhindert Setup-/Modulausfälle durch inkonsistente API-Methoden und stabilisiert den kompletten HA↔Core Kommunikationspfad.

### Netzwerk/Endpoint-Robustheit
- Host/Port-Normalisierung fuer Eingaben wie `http://IP:PORT`, `IP:PORT` und reine Hostnamen.
- Multi-Host-Fallback im Coordinator (konfigurierter Host + interne/externe HA-URL Hosts + `homeassistant.local`/`localhost`/`127.0.0.1`).
- Bei Verbindungsproblemen/5xx wird automatisch auf den nächsten erreichbaren Endpoint gewechselt.

### Setup-Flow Hardening
- Zero-Config und Manual Setup versuchen jetzt aktiv einen erreichbaren Core-Endpoint zu entdecken.
- Wizard-Finalisierung normalisiert/validiert den Ziel-Endpoint vor Entry-Erstellung.
- Legacy-Modul initialisiert optionale Teilschritte jetzt strikt best-effort (webhook/devlog/media/capabilities), statt den gesamten Setup-Pfad zu brechen.

### Version-Anzeige korrigiert
- `entity.py` liest die Integrationsversion dynamisch aus `manifest.json`, damit die in HA angezeigte Version nicht mehr veraltet sein kann.

## [7.7.8] - 2026-02-22 — SETUP ROBUSTNESS PATCH

### Zero-Config / Setup-Resilienz
- `__init__.py` entkoppelt von grossen statischen Top-Level-Imports, die bei einzelnen Modulproblemen die gesamte Integration blockieren konnten.
- Modulregistrierung auf dynamischen Einzelimport umgestellt (`import_module` + `getattr`) mit granularer Fehlerisolierung pro Modul.
- Fehlschlaege einzelner Module werden geloggt und uebersprungen; die Integration selbst bleibt ladbar.

### Versionssync
- Integration-Version auf `7.7.8` angehoben.

## [7.7.7] - 2026-02-22 — PRODUCTION READINESS PROGRAM

### Kommunikationspipeline verstaerkt getestet
- `tests/integration/test_full_flow.py` ersetzt Placeholder durch echte Roundtrip-Validierung:
  - HA Event → N3 Envelope (Privacy/Redaction)
  - Core Candidate → HA Repairs Payload
  - User-Entscheidung → Sync zurueck an Core (`PUT /api/v1/candidates/:id`)

### Konfigurierbarkeit / HA-Kompatibilitaet
- `manifest.json` ergaenzt um `homeassistant: \"2024.1.0\"`.
- Integration-Version auf `7.7.7` angehoben.

### Dauerbetrieb / 15-Minuten Guardrail
- Neuer GitHub-Workflow `production-guard.yml`:
  - geplanter Lauf alle 15 Minuten
  - Syntax-Check + kritische Integrationspfadtests
  - fruehes Erkennen von Regressions im HA↔Core-Loop

### Dokumentation
- Vision und Projektstatus auf aktuellen Release-Stand aktualisiert.

## [7.7.6] - 2026-02-22 — CI RELIABILITY UPDATE

### CI-Workflow gehaertet
- Test-Dependencies im CI erweitert (u.a. `numpy`, `pyyaml`), damit die Suite in GitHub Actions vollständig aufloest.
- Pytest-Job faellt bei Fehlern jetzt korrekt durch (kein `|| true` mehr).

### Verifikation
- Syntax- und JSON-Checks lokal erfolgreich.
- Integration bleibt kompatibel mit Core `7.7.6`.

## [7.7.0] - 2026-02-21 — HA CONFORMITY RELEASE

### Kompletter HA-Konformitaets-Audit — alle Stolperstellen gefixt

#### KRITISCH: Integration lud keine Plattformen
- **legacy.py**: `CopilotDataUpdateCoordinator` war hinter `TYPE_CHECKING` versteckt aber wurde zur Laufzeit benoetigt → `NameError` → KEINE Sensoren/Buttons/etc wurden geladen. GEFIXT.

#### Kaputte Imports
- **quick_search.py**: `..core.module` → `.module`, `..const` → `...const`
- **module_connector.py**: `..const` → `.const`

#### manifest.json
- `homeassistant: "2024.1.0"` Mindestversion hinzugefuegt

#### Sonstiges
- **mood_module.py**: Falscher Default-Port `5000` → `8909`

## [7.6.4] - 2026-02-21 — ADD-ON DISCOVERY FIX

### Sync mit Core v7.6.4

- Core Add-on: `config.json` → `config.yaml` Migration (Schema-Mismatch war Root Cause fuer fehlende Add-on Anzeige im Store)

## [7.6.3] - 2026-02-21 — VERSION ALIGNMENT + REPO HYGIENE

### Sync mit Core v7.6.3

- Version aligned mit Core v7.6.3
- Core hat stale `custom_components/copilot/` Verzeichnis entfernt (Add-on Discovery Fix)

## [7.6.2] - 2026-02-21 — BUGFIX: 3 Echte Bugs gefixt

### Audit & Bugfix Release

#### Fixes
- **energy_context_entities.py**: Metaclass-Konflikt behoben — `Entity` durch `SensorEntity`/`BinarySensorEntity` ersetzt (6 Klassen)
- **voice_context.py**: Kaputte Import-Pfade gefixt (`..core.module` → `.module`, `..const` → `...const`)
- **anomaly_detector.py**: `sklearn` graceful Fallback — ML-Detection deaktiviert wenn sklearn nicht installiert (kein Crash mehr)
- **test_anomaly_detector.py**: Tests skippen automatisch ohne sklearn (`pytest.importorskip`)

#### Tests
- 497 Tests bestanden, 0 Fehler (5 skipped wegen fehlender sklearn)
- Alle 3 vorher kaputten Test-Dateien funktionieren jetzt

## [7.6.0] - 2026-02-21 — PRODUCTION-READY RELEASE

### Bulletproof HA Integration — Bereit fuer echten Test

#### Production Readiness
- Version aligned mit Core v7.6.0
- Core startet jetzt alle 17 Hub-Engines korrekt
- Alle 18 Sensoren koennen Daten von Core abrufen
- 120+ API Endpoints live unter /api/v1/hub/*

#### Vollstaendige Sensor-Liste (18 Sensoren):
1. CopilotStatusSensor — System-Status
2. PredictiveMaintenanceSensor — Wartungsvorhersage
3. AnomalyDetectionSensor — Anomalie-Erkennung
4. GasMeterSensor — Gaszaehler
5. HabitusZoneSensor — Zonen-Erkennung
6. LightIntelligenceSensor — Licht-Intelligence
7. ZoneModeSensor — Zonen-Modi
8. MediaFollowSensor — Media Follow
9. EnergyAdvisorSensor — Energie-Beratung
10. AutomationTemplateSensor — Automation Templates
11. SceneIntelligenceSensor — Szenen-Intelligence
12. PresenceIntelligenceSensor — Anwesenheit
13. NotificationIntelligenceSensor — Benachrichtigungen
14. SystemIntegrationSensor — System Integration
15. BrainArchitectureSensor — Hirnregionen
16. BrainActivitySensor — Brain Pulse/Sleep

#### Infrastructure
- Version bump to 7.6.0

## [7.5.0] - 2026-02-21

### Brain Activity Sensor — Pulse, Sleep & Chat

#### Brain Activity Sensor (NEW)
- **sensors/brain_activity_sensor.py** — `BrainActivitySensor`
- State: "Aktiv — pulsierend" / "Wach — bereit" / "Schlafend"
- Dynamic icons: head-lightbulb (active), brain (idle), power-sleep (sleeping)
- Attributes: pulse count, chat messages, uptime, sleep time, recent activity
- Frontend nutzt state für Brain-Animation (pulse/glow/dim)

#### Infrastructure
- **sensor.py** — Registers BrainActivitySensor
- Version bump to 7.5.0

## [7.4.0] - 2026-02-21

### Brain Architecture Sensor — Hirnregionen, Neuronen & Synapsen

#### Brain Architecture Sensor (NEW)
- **sensors/brain_architecture_sensor.py** — `BrainArchitectureSensor`
- State: "X/Y Regionen aktiv" / "X/Y Regionen — Z% Gesundheit"
- Dynamic icons: brain (healthy), head-alert (degraded), head-remove (critical)
- Attributes: regions mit Farben & Rollen, synapse summary, graph nodes/edges
- Connectivity Score & Health Score Monitoring

#### Infrastructure
- **sensor.py** — Registers BrainArchitectureSensor
- Version bump to 7.4.0

## [7.3.0] - 2026-02-21

### System Integration Sensor — Cross-Engine Monitoring

#### System Integration Sensor (NEW)
- **sensors/system_integration_sensor.py** — `SystemIntegrationSensor`
- State: "X Engines / Y Verknüpfungen" / "Nicht verbunden"
- Dynamic icons: hub (active), hub-outline (idle/disconnected)
- Attributes: engines list, wiring diagram, event log, subscriptions count

#### Infrastructure
- **sensor.py** — Registers SystemIntegrationSensor
- Version bump to 7.3.0

## [7.2.0] - 2026-02-21

### Notification Intelligence Sensor — Smart Benachrichtigungen

#### Notification Intelligence Sensor (NEW)
- **sensors/notification_intelligence_sensor.py** — `NotificationIntelligenceSensor`
- State: "X ungelesen" / "Alle gelesen" / "Keine Benachrichtigungen"
- Dynamic icons: bell-badge (unread), bell-off (DND), bell-check (all read)
- Attributes: stats, DND status, recent notifications, rules, channels

#### Infrastructure
- **sensor.py** — Registers NotificationIntelligenceSensor
- Version bump to 7.2.0

## [7.1.0] - 2026-02-21

### Presence Intelligence Sensor — Anwesenheits-Tracking & Raum-Belegung

#### Presence Intelligence Sensor (NEW)
- **sensors/presence_intelligence_sensor.py** — `PresenceIntelligenceSensor`
- State: "Alle zu Hause" / "Alle abwesend" / "X/Y zu Hause"
- Dynamic icons: home-account, home-export, home-clock
- Attributes: persons home/away, occupied rooms, transitions, triggers

#### Infrastructure
- **sensor.py** — Registers PresenceIntelligenceSensor
- Version bump to 7.1.0

## [7.0.0] - 2026-02-21

### Scene Intelligence Sensor — Intelligente Szenen & PilotSuite Cloud

#### Scene Intelligence Sensor (NEW)
- **sensors/scene_intelligence_sensor.py** — `SceneIntelligenceSensor`
- State: Active scene name or "X Szenen verfügbar"
- Dynamic icons per scene (morning sun, bed, party popper, etc.)
- Attributes: active scene, suggestions, cloud status, categories, learned patterns
- Fetches from `/api/v1/hub/scenes`

#### Infrastructure
- **sensor.py** — Registers SceneIntelligenceSensor
- Version bump to 7.0.0

## [6.9.0] - 2026-02-21

### Automation Templates Sensor — Blueprint-Übersicht

#### Automation Template Sensor (NEW)
- **sensors/automation_template_sensor.py** — `AutomationTemplateSensor`
- State: "X Templates, Y generiert"
- Attributes: categories, popular templates, usage stats
- Fetches from `/api/v1/hub/templates/summary`

#### Infrastructure
- **sensor.py** — Registers AutomationTemplateSensor
- Version bump to 6.9.0

## [6.8.0] - 2026-02-21

### Energy Advisor Sensor — Eco-Score, Sparempfehlungen & Verbrauchsübersicht

#### Energy Advisor Sensor (NEW)
- **sensors/energy_advisor_sensor.py** — `EnergyAdvisorSensor`
- State: "Eco-Score A+ (95/100)" with grade-based icons
- Attributes: eco-score, trend, daily/monthly kWh/EUR, savings potential
- Breakdown by category, top consumers, recommendations
- Fetches from `/api/v1/hub/energy`

#### Infrastructure
- **sensor.py** — Registers EnergyAdvisorSensor
- Version bump to 6.8.0

## [6.7.0] - 2026-02-21

### Media Follow / Musikwolke Sensor — Wiedergabe-Folgen & Playback

#### Media Follow Sensor (NEW)
- **sensors/media_follow_sensor.py** — `MediaFollowSensor`
- State: "Keine Wiedergabe" / "Artist — Title" / "X Wiedergaben"
- Dynamic icons per media type (music, tv, radio, podcast)
- Attributes: active sessions, zones with playback, follow zones, zone states, transfers
- Fetches from `/api/v1/hub/media`

#### Infrastructure
- **sensor.py** — Registers MediaFollowSensor
- Version bump to 6.7.0

## [6.6.0] - 2026-02-21

### Zone Modes Sensor — Party/Sleep/Custom Quick-Switches

#### Zone Mode Sensor (NEW)
- **sensors/zone_mode_sensor.py** — `ZoneModeSensor`
- State: "Keine aktiven Modi" / Mode-Name / "X Modi aktiv"
- Dynamic icons per active mode (party-popper, baby-face, movie, heart, etc.)
- Attributes: active modes with remaining time, available modes, recent events
- Fetches from `/api/v1/hub/modes`

#### Infrastructure
- **sensor.py** — Registers ZoneModeSensor
- Version bump to 6.6.0

## [6.5.0] - 2026-02-21

### Licht-Intelligence Sensor — Sonnenstand, Szenen, Ausleuchtung

#### Light Intelligence Sensor (NEW)
- **sensors/light_intelligence_sensor.py** — `LightIntelligenceSensor`
- State: suggested scene name or sun phase (Tag/Nacht/Dämmerung)
- Dynamic icons per sun phase
- Attributes: sun elevation/azimuth/phase, outdoor lux, scenes, cloud filter
- Fetches from `/api/v1/hub/light`

#### Infrastructure
- **sensor.py** — Registers LightIntelligenceSensor
- Version bump to 6.5.0

## [6.4.0] - 2026-02-21

### Habitus-Zonen Sensor — Room-to-Zone Overview

#### Habitus Zone Sensor (NEW)
- **sensors/habitus_zone_sensor.py** — `HabitusZoneSensor`
- State: "X/Y aktiv" zone count
- Dynamic icon: party-popper (Partymodus) / sleep (Schlafmodus) / home-floor-1
- Attributes: zone count, room count, entity count, mode distribution, unassigned rooms
- Fetches from `/api/v1/hub/zones`

#### Infrastructure
- **sensor.py** — Registers HabitusZoneSensor
- Version bump to 6.4.0

## [6.3.0] - 2026-02-21

### Gaszähler Sensor — Gas Consumption, Costs & Forecast

#### Gas Meter Sensor (NEW)
- **sensors/gas_meter_sensor.py** — `GasMeterSensor`
- State: current meter reading (m³), device_class: gas, state_class: total_increasing
- Attributes: impulses, today/month m³/kWh/EUR, forecast, trend, gas price
- Fetches from `/api/v1/regional/gas`

#### Infrastructure
- **sensor.py** — Registers GasMeterSensor
- Version bump to 6.3.0

## [6.2.0] - 2026-02-21

### Anomaly Detection v2 Sensor — Multi-Dimensional Pattern Analysis

#### Anomaly Detection Sensor (NEW)
- **sensors/anomaly_detection_sensor.py** — `AnomalyDetectionSensor`
- State: "Normal" / "X Anomalien" / "X kritisch"
- Dynamic icon: check-decagram (ok) / alert (warning) / alert-octagon (critical)
- Attributes: entity count, anomaly counts by severity, anomaly types, top 5 anomalies
- Fetches from `/api/v1/hub/anomalies`

#### Infrastructure
- **sensor.py** — Registers AnomalyDetectionSensor
- Version bump to 6.2.0

## [6.1.0] - 2026-02-21

### Predictive Maintenance Sensor — Device Health in HA

#### Predictive Maintenance Sensor (NEW)
- **sensors/predictive_maintenance_sensor.py** — `PredictiveMaintenanceSensor`
- State: average device health score (0-100)
- Dynamic icon: check-decagram (healthy) / wrench-cog (warning) / wrench-clock (critical)
- Attributes: device counts by status, attention list, upcoming maintenance
- Fetches from `/api/v1/hub/maintenance`

#### Infrastructure
- **sensor.py** — Registers PredictiveMaintenanceSensor
- **entity.py** + **manifest.json** — Version 6.1.0

## [6.0.0] - 2026-02-21

### PilotSuite Hub Sensors — Dashboard, Plugins, Multi-Home in HA

#### Hub Dashboard Sensor (NEW)
- **sensors/hub_dashboard_sensor.py** — 3 new sensor entities
- `HubDashboardSensor` — active device count, alerts, savings, layout
- `HubPluginsSensor` — active plugin count, categories, status
- `HubMultiHomeSensor` — home count, online/offline, cross-home totals

#### Infrastructure
- **sensor.py** — Registers all 3 Hub sensors
- **entity.py** + **manifest.json** — Version 6.0.0

## [5.25.0] - 2026-02-21

### EV Charging Sensor — SoC & Smart Charging in HA

#### EV Charging Sensor (NEW)
- **sensors/ev_charging_sensor.py** — `EVChargingSensor` entity
- State: current SoC percentage
- Dynamic icon: ev-station (charging), solar-power (solar), car-electric (ready)
- Attributes: vehicle name, connector, SoC, power, range, time-to-target,
  departure readiness, cost, strategy, solar/grid energy split
- Fetches from `/api/v1/regional/ev/status` and `/ev/schedule`

#### Infrastructure
- **sensor.py** — Registers EVChargingSensor
- **entity.py** + **manifest.json** — Version 5.25.0

## [5.24.0] - 2026-02-21

### Heat Pump Sensor — COP & Scheduling in HA

#### Heat Pump Sensor (NEW)
- **sensors/heat_pump_sensor.py** — `HeatPumpSensor` entity
- State: current COP (coefficient of performance)
- Dynamic icon: heat-pump/water-boiler/solar-power/snowflake-melt based on action
- Attributes: pump type, action, COP, power, room/outdoor/DHW temps,
  runtime, heat/electricity today, cost, strategy, schedule totals
- Fetches from `/api/v1/regional/heatpump/status` and `/heatpump/schedule`

#### Infrastructure
- **sensor.py** — Registers HeatPumpSensor
- **entity.py** + **manifest.json** — Version 5.24.0

## [5.23.0] - 2026-02-21

### Battery Optimizer Sensor — Charge/Discharge Strategy in HA

#### Battery Optimizer Sensor (NEW)
- **sensors/battery_optimizer_sensor.py** — `BatteryOptimizerSensor` entity
- State: current SoC percentage
- Dynamic icon: charging/discharging/high/medium/low based on state
- Attributes: SoC, capacity, action, power, strategy, cycles, savings,
  charge/discharge prices, next charge/discharge times, health

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.23.0

## [5.22.0] - 2026-02-21

### Styx Onboarding Sensor — Setup Progress Tracking in HA

#### Onboarding Sensor (NEW)
- **sensors/onboarding_sensor.py** — `OnboardingSensor` entity
- State: "Schritt X/8" during setup, "Abgeschlossen" when done
- Dynamic icon: school (in progress) → check-decagram (complete)
- Attributes: current/total steps, completed/skipped counts, agent name, timestamps
- Fetches from `/api/v1/onboarding/state`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.22.0

## [5.21.0] - 2026-02-21

### Styx Agent Auto-Config — Default Agent Setup & Connectivity Verification

#### Agent Auto-Config Module (NEW)
- **agent_auto_config.py** — Auto-configure Styx as HA conversation agent
- Bidirectional connectivity verification (HA <-> Core) on startup
- Fires `pilotsuite_agent_ready` event when agent is registered
- 3 new HA services:
  - `ai_home_copilot.set_default_agent` — Register + guide to set as default
  - `ai_home_copilot.verify_agent` — Verify Core connectivity with notification
  - `ai_home_copilot.get_agent_status` — Show full agent status notification

#### Agent Status Sensor (NEW)
- **sensors/agent_status_sensor.py** — `AgentStatusSensor` entity
- State: "Styx: ready" / "Styx: degraded" / "Styx: offline"
- Dynamic icon: robot-happy (ready), robot-confused (degraded), robot-off (offline)
- Attributes: version, uptime, LLM model/backend, character, features, languages

#### Integration Lifecycle
- Auto-config runs after conversation agent registration in `async_setup_entry`
- Services unloaded cleanly in `async_unload_entry`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.21.0

## [5.20.0] - 2026-02-21

### Energy Forecast Sensor — 48h PV/Price/Weather Dashboard in HA

#### Energy Forecast Sensor (NEW)
- **sensors/energy_forecast_sensor.py** — `EnergyForecastSensor` entity
- State: total estimated PV kWh over 48h forecast period
- Icon: mdi:chart-timeline-variant, unit: kWh
- Attributes: total hours, avg/min/max price, cheapest/most expensive hour,
  daylight hours, avg PV factor, best charge/consume windows, weather impacted hours,
  card count, generation timestamp
- Fetches complete dashboard data from `/api/v1/regional/forecast/dashboard`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.20.0

## [5.19.0] - 2026-02-21

### Proactive Alert Sensor — Combined Energy Alerts in HA

#### Proactive Alert Sensor (NEW)
- **sensors/proactive_alert_sensor.py** — `ProactiveAlertSensor` entity
- State: alert count + highest priority (e.g. "3x Kritisch")
- Dynamic icon: check-circle → alert-octagon based on priority
- Attributes: priority breakdown, category breakdown, alert list with titles/actions
- German state labels ("Keine Alerts" when clear)

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.19.0

## [5.18.0] - 2026-02-21

### Tariff Sensor — Dynamic Electricity Pricing in HA

#### Tariff Sensor (NEW)
- **sensors/tariff_sensor.py** — `TariffSensor` entity
- State: current electricity price in ct/kWh
- Dynamic icon: lightning-bolt (low) to flash-alert (high) based on price level
- Attributes: avg/min/max prices, cheapest/most expensive hours, spread, tariff type, source

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.18.0

## [5.17.0] - 2026-02-21

### Fuel Price Sensor — Strom vs Diesel vs Benzin Cost Comparison in HA

#### Fuel Price Sensor (NEW)
- **sensors/fuel_price_sensor.py** — `FuelPriceSensor` entity
- State: electricity cost per 100km (EUR/100km)
- Attributes: electric/diesel/benzin/e10 cost per 100km, cheapest option, CO2 comparison
- Raw fuel prices: avg/min per fuel type, station count, cheapest stations
- Savings vs diesel/benzin calculated automatically
- Fetches both `/fuel/prices` and `/fuel/compare` from Core API

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.17.0

## [5.16.0] - 2026-02-21

### Weather Warning Sensor — DWD/ZAMG/MeteoSchweiz Alerts in HA

#### Weather Warning Sensor (NEW)
- **sensors/weather_warning_sensor.py** — `WeatherWarningSensor` entity
- State: warning count + highest severity (e.g. "2x Unwetterwarnung")
- Dynamic icon: sunny→alert→alert-octagon based on severity level
- Attributes: total warnings, severity breakdown, PV impact, grid risk, max PV reduction %, recommendations
- Warning list with headline, severity, type, region, color for each active warning
- German "Keine Warnungen" state when clear

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.16.0

## [5.15.0] - 2026-02-21

### Regional Context Sensor — Zero-Config Location Awareness in HA

#### Regional Context Sensor (NEW)
- **sensors/regional_context_sensor.py** — `RegionalContextSensor` entity
- State: country + region (e.g. "DE — Brandenburg/Berlin")
- Auto-syncs location from HA zone.home to Core on first update (zero-config)
- Attributes: lat, lon, country, region, timezone, sunrise, sunset, solar elevation, grid price, weather service

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.15.0

## [5.14.0] - 2026-02-21

### Demand Response Sensor — Grid Signal Monitoring in HA

#### Demand Response Sensor (NEW)
- **sensors/demand_response_sensor.py** — `DemandResponseSensor` entity
- State: current signal level (Normal/Advisory/Moderate/Critical)
- Dynamic icon: tower→alert→alert-octagon based on severity
- Attributes: active signals, managed devices, curtailed count, total reduction watts, response active

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.14.0

## [5.13.0] - 2026-02-21

### Energy Report Sensor — Weekly Report Highlights in HA

#### Energy Report Sensor (NEW)
- **sensors/energy_report_sensor.py** — `EnergyReportSensor` entity
- State: weekly net cost in EUR
- Attributes: period, consumption, production, autarky %, solar savings, trend, highlights, recommendation count
- Fetches weekly report from Core `POST /api/v1/energy/reports/generate`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.13.0

## [5.12.0] - 2026-02-21

### Appliance Fingerprint Sensor — Device Recognition in HA

#### Appliance Fingerprint Sensor (NEW)
- **sensors/appliance_fingerprint_sensor.py** — `ApplianceFingerprintSensor` entity
- State: count of known device fingerprints
- Attributes: top 5 fingerprints (id, name, type, avg watts), top 5 usage stats (runs, kWh)
- Dual endpoint polling: fingerprints + usage stats

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.12.0

## [5.11.0] - 2026-02-21

### Weather Optimizer Sensor — Forecast-Based Energy Insights in HA

#### Weather Optimizer Sensor (NEW)
- **sensors/weather_optimizer_sensor.py** — `WeatherOptimizerSensor` entity
- State: number of optimal consumption windows found
- Attributes: total PV kWh, avg price, best/worst hours, alerts, top 3 windows, battery actions, self-consumption %
- Async fetch from Core `GET /api/v1/predict/weather-optimize`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.11.0

## [5.10.0] - 2026-02-21

### Energy Cost Sensor — Cost Tracking in HA

#### Energy Cost Sensor (NEW)
- **sensors/energy_cost_sensor.py** — `EnergyCostSensor` entity
- State: weekly total cost in EUR (e.g. "32.50")
- Attributes: period, avg daily cost, total consumption, total savings, budget status (spent, remaining, percent used, on-track)
- Async fetch from Core `GET /api/v1/energy/costs/summary` and `GET /api/v1/energy/costs/budget`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.10.0

## [5.9.0] - 2026-02-21

### Automation Suggestion Sensor — Smart Recommendations in HA

#### Automation Suggestion Sensor (NEW)
- **sensors/automation_suggestion_sensor.py** — `AutomationSuggestionSensor` entity
- State: suggestion count (e.g. "3 suggestions")
- Attributes: top 3 suggestions with title/category/confidence/savings, category breakdown, total savings
- Async fetch from Core `GET /api/v1/automations/suggestions`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.9.0

## [5.8.0] - 2026-02-21

### Notification Sensor — Alert Monitoring in HA

#### Notification Sensor (NEW)
- **sensors/notification_sensor.py** — `NotificationSensor` entity
- State: pending alert count (e.g. "3 pending" or "no alerts")
- Dynamic icon: bell-alert when pending, bell-outline when clear
- Attributes: latest 5 notifications, 24h digest with by-source/by-priority counts
- Dual endpoint polling: notifications + digest

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.8.0

## [5.7.0] - 2026-02-21

### Comfort Index Sensor — Environmental Comfort in HA

#### Comfort Index Sensor (NEW)
- **sensors/comfort_index_sensor.py** — `ComfortIndexSensor` entity
- State: composite comfort score (0-100 points)
- Dynamic icon based on grade (happy/neutral/sad emoji)
- Attributes: grade, per-factor scores (temperature, humidity, air quality, light), suggestions, zone
- Async fetch from Core `GET /api/v1/comfort`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.7.0

## [5.6.0] - 2026-02-21

### Dashboard Card Generator — Auto-generate Lovelace YAML

#### Card Generator Module (NEW)
- **dashboard/card_generator.py** — Auto-generates Lovelace card configurations
- `generate_energy_overview_card()` — Consumption/production/power gauges with severity thresholds
- `generate_schedule_card()` — Device schedule table with Jinja2 templates for live updates
- `generate_sankey_card()` — Iframe embedding Core's SVG Sankey diagram
- `generate_zone_cards()` — Per-zone energy breakdown with graph footer
- `generate_anomaly_card()` — Conditional anomaly alerts
- `generate_full_dashboard()` — Complete energy dashboard view (configurable sections)
- `dashboard_to_yaml()` — Full YAML export for Lovelace import

#### Test Suite (NEW — 30+ tests)
- **tests/test_card_generator.py**
  - `TestEnergyOverviewCard` — Gauges, severity levels, power max
  - `TestScheduleCard` — Entity card, Jinja2 markdown table
  - `TestSankeyCard` — Iframe URL, SVG endpoint, aspect ratio
  - `TestZoneCards` — Empty zones fallback, multi-zone stacks, footer graphs
  - `TestAnomalyCard` — Conditional type, markdown content
  - `TestFullDashboard` — Section inclusion/exclusion, zone handling
  - `TestYAMLExport` — Valid YAML, views structure, zone support

#### Infrastructure
- **dashboard/__init__.py** — New module with public exports
- **entity.py** + **manifest.json** — Version 5.6.0

## [5.5.0] - 2026-02-21

### Energy Schedule Sensor — Daily Device Schedule in HA

#### Energy Schedule Sensor (NEW)
- **sensors/energy_schedule_sensor.py** — `EnergyScheduleSensor` entity
- Shows next scheduled device as sensor state (e.g. "washer at 11:00")
- Exposes attributes: date, devices_scheduled, total cost estimate, PV coverage %, peak load
- Per-device schedule breakdown with hours, cost, and PV percentage
- URLs for daily schedule and next-device API endpoints
- Async fetches from Core `GET /api/v1/predict/schedule/daily`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.5.0

## [5.4.0] - 2026-02-21

### OpenAPI Spec v5.4.0 — Version Sync

#### Version Sync
- Synchronized with PilotSuite Core v5.4.0 (OpenAPI Spec update)
- Core now serves 49 API paths with 64 component schemas
- Complete Energy API documentation available at `/api/v1/docs`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.4.0

## [5.3.0] - 2026-02-21

### Test Coverage — Voice Context + Anomaly Detector

#### Voice Context Tests (NEW — 45+ tests)
- **tests/test_voice_context.py**
  - `TestCommandPattern` — Regex matching, case insensitivity, entity extraction, multiple patterns
  - `TestExtractors` — Temperature, scene, automation, entity extraction functions
  - `TestParseCommand` — All 16 intents: light on/off/toggle, climate warmer/cooler/set, media play/pause/stop, volume up/down, scene, automation, status, search, help, unknown
  - `TestVoiceTone` — Tone config switching (formal/friendly/casual/cautious), character service integration, response formatting fallbacks
  - `TestTTSDiscovery` — Priority-based entity discovery (Sonos, Google Home, TTS capability, fallback)
  - `TestSpeak` — TTS service calls, custom entity, failure fallback to media_player
  - `TestModuleProperties` — Name, version, help text
  - `TestDataclasses` — VoiceCommand, TTSRequest defaults and custom values
  - `TestCommandPatternsCoverage` — Ensures all defined intents are reachable

#### Anomaly Detector Tests (NEW — 35+ tests)
- **tests/test_anomaly_detector.py**
  - `TestInit` — Default/custom params, empty initial state
  - `TestFeatures` — Feature initialization, buffer sizes, vector extraction, missing/non-numeric values
  - `TestFit` — Model fitting, disabled state, random seed, error fallback
  - `TestUpdate` — Not-fitted, disabled, normal/anomalous values, history tracking, missing features
  - `TestScoring` — Score range validation, exception handling
  - `TestAdaptiveThreshold` — Default (cold start), high/low/medium anomaly rates
  - `TestSummary` — Empty, with data, time filter
  - `TestReset` — State clearing, feature history clearing
  - `TestContextAware` — ContextAwareAnomalyDetector: init, temporal analysis, relationship analysis, context defaults
  - `TestEdgeCases` — History/window max size, empty features, multiple sequential updates

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.3.0

## [5.2.0] - 2026-02-21

### Sankey Energy Flow Sensor

#### Energy Sankey Sensor (NEW)
- **sensors/energy_sankey_sensor.py** — `EnergySankeySensor` entity
- Exposes energy Sankey flow data from Core API as HA sensor
- Attributes: sankey_svg_url, sankey_json_url, sources, consumers, node/flow counts
- State shows node and flow count summary

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.2.0

## [5.1.0] - 2026-02-21

### Zone Energy Device Discovery — Auto-Association + Tagging

#### Zone Energy Discovery Module (NEW)
- **zone_energy_devices.py** — `ZoneEnergyDiscovery` class for automatic energy device detection per Habitzone
- `ZoneEnergyDevice` dataclass — entity_id, device_class, related_entities, association_method, tags
- 3 auto-discovery strategies:
  1. **Device-based**: Energy sensors sharing `device_id` with zone entities
  2. **Area-based**: Energy sensors in the same HA area
  3. **Name-based**: Energy sensor names matching zone entity/zone name patterns
- `discover_all_energy_entities()` — Scans HA entity registry for power/energy/current/voltage device classes
- `discover_for_zone(zone_entity_ids, zone_name)` — Auto-discovers energy devices for a specific Habitzone
- `get_zone_power_total(energy_entity_ids)` — Aggregates power with unit conversion (kW→W, mW→W)
- Uses HA registries: `entity_registry`, `device_registry`, `area_registry`

#### Infrastructure
- **entity.py** + **manifest.json** — Version 5.1.0

## [5.0.0] - 2026-02-21

### Major Release — Performance Monitoring, Test Coverage

#### Performance Monitoring Module (EXPANDED)
- **performance_scaling.py** — Expanded from v0.1 stub (54 lines) to v1.0 kernel (314 lines)
- API response time tracking with rolling window (500 samples) and percentiles (p50/p90/p95/p99)
- Memory usage monitoring via `/proc/self/status` (Linux)
- Entity count metrics for PilotSuite entities
- Coordinator update latency tracking
- Configurable alert thresholds (API time, coordinator, entity count, memory, error rate)
- Background monitoring loop (60s interval) with alert generation
- Integration with existing PerformanceGuardrails rate limiting
- `get_snapshot()`, `get_percentiles()`, `get_guardrails_status()` query API

#### Test Coverage (+4 test files, ~60 new tests)
- **test_performance_scaling.py** (NEW) — 16 tests: recording, snapshot, percentiles, thresholds, alerts, edge cases
- **test_energy_context.py** (NEW) — 14 tests: frugality scoring, mood dict, snapshot, edge cases
- **entity.py** + **manifest.json** — Version 5.0.0

## [1.0.0] - 2026-02-21

### Stable Release — Feature-Complete

PilotSuite Styx HACS Integration erreicht **v1.0.0 Stable**. Alle geplanten Meilensteine sind abgeschlossen.

**Cumulative seit v4.0.0:**
- **v4.1.0** Race Conditions Fix (asyncio.Lock)
- **v4.2.0** History Backfill (HA Recorder → Core, einmalig)
- **v4.2.1** Hassfest + Config Flow Fix
- **v4.3.0** Mood Persistence (HA Storage API, 24h TTL Cache)
- **v4.4.0** Test Coverage: 14 neue Tests (Mood Store + Cache)
- **v4.5.0** Conflict Resolution Engine (ConflictResolver + PreferenceInputCard + 11 Tests)

**Gesamtbilanz:**
- 94+ Sensoren, 30 Module, 22+ Dashboard Cards
- 3 Native Lovelace Cards (Brain Graph, Mood, Habitus)
- HA Conversation Agent (Styx → Core `/v1/chat/completions`)
- Conflict Resolution (weighted/compromise/override)
- Config Flow (Zero Config, Quick Start, Manual)
- Deutsch + Englisch Translations
- CI/HACS/Hassfest gruen

## [4.5.0] - 2026-02-21

### Conflict Resolution Engine

- **conflict_resolution.py** — Neues Modul: Erkennt und loest Praeferenz-Konflikte zwischen aktiven Nutzern; paarweiser Divergenz-Check auf allen Mood-Achsen (Schwellenwert 0.3); drei Strategien: `weighted` (prioritaetsgewichtet), `compromise` (Durchschnitt), `override` (einzelner Nutzer gewinnt)
- **preference_input_card.py** — Umgeschrieben: Zeigt Konflikt-Status als HA-Entity mit `state: conflict|ok`; Extra-Attribute: aktive Konflikte, Strategie, beteiligte Nutzer, aufgeloester Mood, Konflikt-Details
- **test_conflict_resolution.py** — 11 neue Tests: Konflikt-Erkennung, alle 3 Strategien, Serialisierung, Edge Cases
- **manifest.json** + **entity.py** Version auf 4.5.0 synchronisiert

## [4.4.0] - 2026-02-21

### Test Coverage + Quality

- **test_mood_store.py** — 8 neue Tests fuer Mood State Persistence (save/load/TTL/roundtrip/edge cases)
- **test_mood_context_cache.py** — 6 neue Tests fuer MoodContextModule Cache-Integration (pre-load/fallback/idempotenz)
- **manifest.json** + **entity.py** Version auf 4.4.0 synchronisiert
- Gesamte Test Suite: 352 Tests bestanden, 0 Fehler

## [4.3.0] - 2026-02-20

### Mood Persistence + MUPL Role Sync

- **mood_store.py** — Neues Modul: Mood-Snapshots werden via HA Storage API lokal zwischengespeichert; bei HA-Restart wird gecachter Mood sofort geladen (kein Warten auf Core); Cache-TTL 24h, danach automatische Invalidierung
- **mood_context_module.py** — Beim Start: Pre-Load aus HA-Cache; bei jedem Core-Fetch: automatische Persistenz; bei Timeout: Fallback auf lokalen Cache statt leeres Mood-Objekt; `_using_cache` Flag für Diagnostik
- **manifest.json** + **entity.py** Version auf 4.3.0 synchronisiert

## [4.2.1] - 2026-02-20

### Bugfix — Hassfest + Config Flow Fix

- **manifest.json** — Ungültigen `homeassistant`-Key entfernt (hassfest: `extra keys not allowed @ data['homeassistant']`); dieser Key wurde von neueren HA-Versionen als invalide abgelehnt und verhinderte das Laden der Integration → "Invalid handler specified" Config Flow Error behoben
- **hacs.json** — Minimum HA-Version (`2024.1.0`) korrekt in `hacs.json` statt `manifest.json` deklariert
- **manifest.json** + **entity.py** Version auf 4.2.1 synchronisiert

## [4.2.0] - 2026-02-20

### History Backfill

- **history_backfill.py** — Neues Modul: Beim ersten Start werden letzte 24h aus dem HA Recorder geladen und als Events an Core gesendet; Brain Graph lernt sofort aus bestehender History; einmalig, Completion wird in HA Storage gespeichert
- **__init__.py** — History Backfill Modul registriert (nach events_forwarder)
- **manifest.json** + **entity.py** Version auf 4.2.0 synchronisiert

## [4.1.0] - 2026-02-20

### Race Conditions + Stability

- **events_forwarder.py** — `asyncio.Lock` ersetzt boolean `flushing` Flag; eliminiert Two-Phase-Flush Race Condition (flushing=False → re-acquire Pattern); Lock wird nie deadlocken
- **manifest.json** + **entity.py** Version auf 4.1.0 synchronisiert

## [4.0.1] - 2026-02-20

### Patch — Version-Fix, Branding-Cleanup, Add-on Store Fix

- **entity.py VERSION** auf 4.0.1 aktualisiert (war 3.13.0 — HACS zeigte falsche Version)
- **manifest.json version** auf 4.0.1 synchronisiert
- **README.md** Header von v3.9.1 auf v4.0.1 aktualisiert
- **camera_dashboard.py** Dashboard-Pfad `ai-home-copilot-camera` → `pilotsuite-camera`
- **docs/USER_MANUAL.md** Version-Header, Card-Types und Anchor-Links aktualisiert
- **PROJECT_STATUS.md** Alpha-Referenzen durch v4.0.x ersetzt
- Alte Version-Kommentare in `__init__.py` bereinigt

## [4.0.0] - 2026-02-20

### Official Release — Repository Rename + Feature-Complete

**Repository umbenannt:** `ai-home-copilot-ha` → `pilotsuite-styx-ha`
Alle internen URLs, Dokumentation und Konfigurationsdateien aktualisiert.
GitHub leitet alte URLs automatisch weiter (301 Redirect).

#### Warum v4.0.0?

Dies ist der erste offizielle Release von PilotSuite Styx als feature-complete Produkt.
Alle Komponenten sind synchron auf v4.0.0:

| Komponente | Repo | Version |
|-----------|------|---------|
| **Core Add-on** | `pilotsuite-styx-core` | 4.0.0 |
| **HACS Integration** | `pilotsuite-styx-ha` | 4.0.0 |
| **Adapter** | `pilotsuite-styx-core` (Unterverzeichnis) | 4.0.0 |

#### Feature-Ueberblick (Cumulative seit v0.14.x)

**30 Coordinator-Module**
- `events_forwarder` — Event Bridge zum Core Add-on (Quality Metrics, Queue)
- `brain_graph_sync` — Brain Graph Synchronisation (WebSocket + REST Fallback)
- `habitus_miner` — Pattern Mining aus Nutzerverhalten (Persistence, Cleanup)
- `mood` + `mood_context` — Mood Tracking + Context-Injection
- `energy_context` — Energieverbrauch pro Zone
- `weather_context` — Wetter-Einfluss auf Vorschlaege
- `network` (UniFi) — Netzwerk-Health, Client-Tracking
- `camera_context` — Kamera-Integration (Frigate Bridge)
- `ml_context` — ML Pattern Recognition
- `voice_context` — Sprach-Interaktions-Tracking
- `home_alerts` — Benachrichtigungen (Persistenz via HA Storage)
- `character_module` — Charakter-Presets fuer Styx
- `waste_reminder` — Muellabfuhr-Erinnerungen (TTS + Notifications)
- `birthday_reminder` — Geburtstags-Erinnerungen (14-Tage Vorschau)
- `entity_tags` — Manuelles Tag-System (Registry, Assignment, Sync)
- `person_tracking` — Anwesenheit (Presence Map, History)
- `frigate_bridge` — NVR-Integration (Person/Motion Detection)
- `scene_module` — Szenen (Capture, Apply, Presets)
- `homekit_bridge` — Apple HomeKit Expose
- `calendar_module` — HA Kalender-Integration
- `media_zones` — Musikwolke + Player-Zonen
- `candidate_poller` — Brain Graph Kandidaten
- `dev_surface` — Debug-Interface
- `performance_scaling` — Auto-Scaling
- `knowledge_graph_sync` — Knowledge Graph Sync
- `ops_runbook` — Operational Runbooks
- `quick_search` — Schnellsuche
- `legacy` — Abwaertskompatibilitaet
- `unifi_module` — UniFi-spezifische Features

**110+ HA Entities**
- 80+ Sensoren (Version, Status, Mood, Habitus, Energy, Network, Predictions, ...)
- 22+ Buttons (Debug, Forwarder, Brain Graph, Mood, Tags, ...)
- Numbers, Selects, Text-Entities, Binary Sensors

**30+ HA Services**
- Tag Registry (upsert, assign, confirm, sync, pull)
- Media Context v2 (suggest zones, apply, clear)
- Event Forwarder (start, stop, stats)
- Ops Runbook (preflight, smoke test, execute, checklist)
- Debug (enable, disable, clear errors, ping)
- Habitus Mining (mine, get rules, reset, configure)
- Multi-User Preferences (learn, priority, delete, export, detect, mood)
- Candidate Poller, UniFi, Energy, Anomaly, Habit Learning, Predictive, HomeKit

**Config Flow**
- Zero Config: Ein-Klick Installation mit Auto-Discovery
- Quick Start Wizard: 7-Schritt Konfiguration
- Manual Setup: Volle Kontrolle ueber alle Parameter
- Options Flow: Nachtraegliche Anpassung aller Einstellungen
- Entity Tags Management im Config Flow

**Dashboard Cards (22+ Typen)**
- Uebersicht, Brain Graph, Habitus Zonen, Mood, Energy
- Presence, Muellabfuhr, Geburtstage, Kalender
- Media Zonen, HomeKit, Szenen, Suggestions
- Mobile-Responsive, Dark Mode, Interactive Filters

**HA Conversation Agent**
- `StyxConversationAgent`: Nativ in HA Assist Pipeline
- Proxy zu Core `/v1/chat/completions`
- DE + EN Unterstuetzung

**3 Native Lovelace Cards**
- `styx-brain-card.js`: Brain Graph Force-Directed Layout
- `styx-mood-card.js`: Mood Circular Gauges
- `styx-habitus-card.js`: Pattern Liste mit Confidence Badges

**Translations**
- Deutsch (de.json) — 23KB, vollstaendig
- English (en.json) — 22KB, vollstaendig

#### Aenderungen in v4.0.0

- **Repository Rename**: `ai-home-copilot-ha` → `pilotsuite-styx-ha`
- **Alle URLs aktualisiert**: manifest.json, openapi.yaml, Docs, README
- **Cross-Referenzen**: `Home-Assistant-Copilot` → `pilotsuite-styx-core` in allen Docs
- **manifest.json**: `homeassistant: "2024.1.0"` Minimum-Version hinzugefuegt

## [3.9.1] - 2026-02-20

### HA Conformity & Cleanup Release

- **entity.py** — device_info now uses `DeviceInfo` dataclass (HA best practice)
  - `manufacturer`: "Custom" → "PilotSuite"
  - `model`: "MVP Core" → "HACS Integration"
  - `sw_version`: now reports current version (3.9.1)
- **coordinator.py** — removed redundant `_hass` attribute (already inherited from `DataUpdateCoordinator`)
  - Fixed: `Dict` → `dict` (Python 3.11+ built-in generics)
- **config_flow.py** — fixed "OpenClaw Gateway" → "PilotSuite Core Add-on" in manual setup
- **media_context.py** — removed module-level `warnings.warn()` that fired on every import
  - Cleaned docstring, kept as base class for media_context_v2
- **manifest.json** — added `homeassistant: "2024.1.0"` minimum version
- **Branding** — 30+ references updated from "AI Home CoPilot" → "PilotSuite":
  - camera_entities.py manufacturer fields (4x)
  - button_debug_ha_errors.py button name
  - ha_errors_digest.py notification titles (4x)
  - pilotsuite_dashboard.py titles and headers (4x)
  - config_wizard_steps.py entry title
  - debug.py device_info
  - setup_wizard.py entry title
  - services_setup.py docstring
- **Core Add-on** — config.json version bump 3.9.0 → 3.9.1, port description updated
- **Adapter** — manifest.json name updated to "PilotSuite (Adapter)", version 3.9.1

## [3.9.0] - 2026-02-20

### Full Consolidation — Alles in einer Version

- **Branch-Konsolidierung** — Alle Arbeit aus 15 Remote-Branches zusammengeführt:
  - `development` (v0.4.0–v0.7.5 Feature-History)
  - `dev/autopilot-2026-02-15` (ML, CI/CD, Knowledge Graph, Neural System, D3.js Brain Graph)
  - `dev/openapi-spec-v0.8.2` (OpenAPI Spec, LazyHistoryLoader)
  - `dev/vector-store-v0.8.3` (Vector Store Client)
  - `dev/mupl-phase2-v0.8.1` (Multi-User Preference Learning)
  - `wip/phase4-ml-patterns` (ML Pattern Recognition)
  - `wip/module-unifi_module` (Module Architecture Fixes)
  - `backup/pre-merge-20260216`, `backup/2026-02-19` (Docs, Reports, Archive)
  - `claude/research-repos-scope-4e3L6` (DeepSeek-R1 Audit)
- **79 Dateien konsolidiert** — Button-Module, Docs, Archive, Reports, Notes, OpenAPI Spec
- **Version vereinheitlicht** — manifest.json auf 3.9.0 (beide Repos synchron)
- **Nichts verloren** — Jede einzigartige Datei aus jedem Branch wurde eingesammelt

### Production-Ready Bug Sweep

- **CRITICAL: `sensor.py` — `data.version` AttributeError** — `CopilotVersionSensor` accessed
  `self.coordinator.data.version` but data is a `dict`. Fixed to `.get("version", "unknown")`.
  This crashed on every coordinator update.
- **`text.py` — unsafe coordinator access** — `async_setup_entry` used double bracket access
  `hass.data[DOMAIN][entry.entry_id]["coordinator"]`. Changed to safe `.get()` chain with
  guarded early-return. Prevents `KeyError` during platform setup.
- **`select.py` — unsafe `hass.data` access** — Same bracket-access pattern. Added safe
  `.get()` chain + coordinator None guard + logging.
- **`seed_adapter.py` — unsafe dict write** — Wrote to `hass.data[DOMAIN][entry.entry_id]`
  without checking existence. Changed to safe `.get()` with isinstance guard.
- **`habitus_dashboard_cards_service.py` — unsafe dict access** — Direct bracket access to
  `hass.data[DOMAIN][entry.entry_id]`. Changed to safe `.get()` chain.
- **`habitus_miner.py` — periodic task resource leak** — Two `async_track_time_interval()`
  calls (cleanup + persistence) did not store unsubscribe functions. Tasks leaked on module
  unload. Now stored in `module_data["listeners"]` for proper cleanup.

## [3.8.1] - 2026-02-19

### Startup Reliability Patch

- **Coordinator safety** — `binary_sensor.py`, `button.py`, `number.py`, `knowledge_graph_entities.py`
  all used unsafe `data["coordinator"]` direct dict access. Changed to `.get("coordinator")` with
  a guarded early-return and error log. Prevents `KeyError` if coordinator is not yet available
  during platform setup ordering.

## [3.8.0] - 2026-02-19

### Persistent State — Alerts & Mining Buffer

- **Alert State persistence** — HomeAlertsModule now persists acknowledged alert IDs
  and daily alert history (30 days) via HA Storage. Acknowledged alerts survive restarts.
  New `get_alert_history(days)` API for trend analysis.
- **Habitus Mining Buffer persistence** — HabitusMinerModule event buffer and discovered
  rules now persist via HA Storage. Buffer saved every 5 minutes + on unload.
  No more cold-start data loss after HA restart.
- **Documentation** — New `docs/QA_SYSTEM_WALKTHROUGH.md`: comprehensive Q&A covering
  all 33 modules, startup sequence, learning pipeline, and persistence guarantees.
- **Version references updated** — README.md, VISION.md, PROJECT_STATUS.md now reflect v3.8.0

## [3.7.1] - 2026-02-19

### Error Isolation — Modul-Setup

- **`__init__.py`** — Alle Modul-Registrierungen in `_get_runtime` einzeln in `try/except`
  - Ein defektes Modul crasht nicht mehr den kompletten Start
- **`async_setup_entry`** — `UserPreferenceModule` und `MultiUserPreferenceModule`
  Setup-Blöcke jeweils in `try/except` gekapselt
  - Optionale Module können ausfallen ohne die Integration zu blockieren
- Version: 3.7.0 → 3.7.1

## [3.7.0] - 2026-02-19

### Bug Fixes & Production Readiness

- **Brain Graph Sync** — Race condition fixes
  - `_processed_events.pop()` crash: replaced with atomic `set()` reset
  - `_send_node_update`/`_send_edge_update`: Null-guard for `_session`
- **Config Validation** — Bounds checking for all 15+ numeric parameters
  - `config_schema_builders.py`: `vol.Range()` on port, intervals, sizes, queue params
  - `validate_input()`: Validates host, port (1-65535), and critical bounds
- **User Hints** — `accept_suggestion()` now creates HA automations via `automation.create`
- **Active Learning** — `_learn_from_context()` records light brightness patterns
  per user/zone/time_slot (was: stub that only logged)
- **Habitus History** — `_fetch_ha_history()` fetches from HA Recorder
  via `state_changes_during_period` (was: always returned `[]`)
- Version: 3.6.0 → 3.7.0

## [3.6.0] - 2026-02-19

### Production Hardening

- **CI Pipeline erweitert** — Full pytest Suite + pytest-cov + bandit Security Scan
  - Vorher: Nur 3 isolierte Tests; jetzt: gesamtes `tests/` Verzeichnis
  - Neuer `security` Job: bandit scannt auf SQL-Injection, Command-Injection, etc.
- Version: 3.5.0 -> 3.6.0

## [3.5.0] - 2026-02-19

### RAG Pipeline + Kalender-Integration

- **Calendar Module** — Integriert alle HA `calendar.*` Entities
  - `core/modules/calendar_module.py`: Auto-Discovery, Event-Abruf, LLM-Kontext
  - `async_get_events_today()`, `async_get_events_upcoming(days)` via HA calendar.get_events
  - Sensor: `sensor.ai_home_copilot_calendar` — Kalender-Count + Liste
  - LLM-Kontext: Zeigt heutige/morgige Termine automatisch
- **Registrierung in __init__.py**: CalendarModule im CopilotRuntime
- Version: 3.4.0 -> 3.5.0

## [3.4.0] - 2026-02-19

### Scene Module + Auto Styx Tagging + HomeKit Bridge

- **Scene Module** — Speichert aktuelle Habituszonen-Zustaende als HA-Szenen
  - `scene_store.py`: HA Storage CRUD mit ZoneScene Dataclass
  - `core/modules/scene_module.py`: Capture, Apply, Delete, Presets, LLM-Kontext
  - 8 Built-in Presets: Morgen, Tag, Abend, Nacht, Film, Party, Konzentration, Abwesend
  - Sensor: `sensor.ai_home_copilot_zone_scenes` — Szenen-Count + Summary
  - Translations (en/de) fuer Config Flow
- **Auto Styx Tagging** — Jede Entitaet mit der Styx interagiert wird automatisch getaggt
  - `entity_tags_module.py` v0.2.0: `async_auto_tag_styx()` Method
  - STYX_TAG_ID "styx" mit lila Farbe + robot Icon
  - `is_styx_entity()`, `get_styx_entities()` Abfragen
  - LLM-Kontext zeigt Styx-getaggte Entitaeten + Anzahl
- **HomeKit Bridge Module** — Exponiert Habituszonen-Entitaeten an Apple HomeKit
  - `core/modules/homekit_bridge.py`: Zone Enable/Disable, Auto-Reload
  - HA Storage Persistenz, `homekit.reload` Service (Pairing bleibt erhalten)
  - Sensor: `sensor.ai_home_copilot_homekit_bridge` — Zonen/Entitaeten Count
  - LLM-Kontext: Zeigt HomeKit-aktive Zonen
- **Dashboard**: Szene-Speichern + HomeKit Button auf Habituszonen-Karten
- Version: 3.3.0 -> 3.4.0

## [3.3.0] - 2026-02-19

### Personen-Tracking + Frigate-Integration

- **Person Tracking Module** — Verfolgt Anwesenheit über HA `person.*` + `device_tracker.*`
  - Live-Presence-Map: Wer ist wo (Zone, seit wann, Quelle)
  - Ankunft/Abfahrt-History mit Event-Erkennung
  - LLM-Kontext: "Anwesend: Max (Wohnzimmer, seit 14:30). Abwesend: Lisa."
  - Sensor: `sensor.ai_home_copilot_persons_home` — Anzahl + Presence-Map
- **Frigate Bridge Module** — Optionale NVR-Integration (auto-disabled wenn kein Frigate)
  - Auto-Discovery von `binary_sensor.*_person` + `binary_sensor.*_motion`
  - Person/Motion-Events → CameraContext Bus-Events
  - Recent Detections Timeline + LLM-Kontext
  - Sensor: `sensor.ai_home_copilot_frigate_cameras`
- Version: 3.2.3 → 3.3.0

## [3.2.3] - 2026-02-19

### Bugfixes

- **Fix: Sensor-Crashes bei None-Modul** — 5 Sensoren hatten fehlende None-Guards in `native_value`:
  `WasteNextCollectionSensor`, `WasteTodayCountSensor`, `BirthdayTodayCountSensor`,
  `BirthdayNextSensor`, `EntityTagsSensor` — geben jetzt 0/None zurück statt AttributeError
- **Fix: Fehlende Translations** — `entity_tags`, `neurons`, `add_tag`, `edit_tag`, `delete_tag`
  Menü-Einträge fehlten in `en.json` + `de.json` → HA zeigte Rohschlüssel statt lesbaren Text
- Version: 3.2.2 → 3.2.3

## [3.2.2] - 2026-02-19

### Tags, Suggestions & Hauswirtschaft

- **Entity Tags System** — Manuelle Entitäts-Tags über den Config Flow verwalten
  - Tags definieren (Name, Farbe, Icon, Modul-Hints), beliebige HA-Entitäten zuordnen
  - Neues Config-Flow-Menü: *Entity-Tags* (Hinzufügen / Bearbeiten / Löschen)
  - `entity_tags_module.py` — CopilotModule: liefert Tag-Kontext an das LLM
  - `entity_tags_store.py` — HA Storage-Persistenz (Store-Key `ai_home_copilot.entity_tags`)
  - Sensor: `sensor.ai_home_copilot_entity_tags` — aktive Tag-Anzahl + Tag-Attribute
- **Entity Assignment Suggestions** — Vorschlagspanel auf der Habitus-Seite im Dashboard
  - Erkennt Entitäten, die keiner Habitus-Zone zugeordnet sind
  - Gruppiert nach Raum-Hint (heuristisch aus Entity-ID extrahiert)
  - Konfidenz-Score (Entitäten-Anzahl + Domain-Diversität)
  - Direkt auf der Habitus-Seite sichtbar

## [3.2.1] - 2026-02-19

### Fixes + Modul-Sweep

- **Fix: Enable-Flags enforced** — `waste_enabled: false` / `birthday_enabled: false` im Config Flow
  werden jetzt korrekt ausgewertet; Module überspringen das Setup vollständig wenn deaktiviert
- **Fix: Neue HA Sensor-Entities** (6 neue Sensoren)
  - `sensor.ai_home_copilot_waste_next_collection` — nächste Abfuhr (Typ + Tage)
  - `sensor.ai_home_copilot_waste_today_count` — Anzahl Abfuhren heute
  - `sensor.ai_home_copilot_birthday_today_count` — Anzahl Geburtstage heute
  - `sensor.ai_home_copilot_birthday_next` — nächster Geburtstag (Name + Tage)
  - `sensor.ai_home_copilot_character_preset` — aktives Charakter-Preset (Modul-Sweep)
  - `sensor.ai_home_copilot_network_health` — Netzwerk-Gesundheit: healthy/degraded/offline (Modul-Sweep)
- **Fix: pilotsuite.create_automation** — `numeric_state` Trigger + optionale Conditions
  - Ermöglicht feuchtigkeitsbasierte Automationen: "Wenn Bad > 70% Luftfeuchtigkeit"
  - `conditions` Array: numeric_state + template Bedingungen

## [3.2.0] - 2026-02-19

### Müllabfuhr + Geburtstags-Erinnerungen

- **Waste Reminder Module**: Optionales Modul für `waste_collection_schedule` Integration
  - Auto-Discovery von Waste-Sensoren (`daysTo` Attribut)
  - Abend-Erinnerung (Vorabend, konfigurierbare Uhrzeit)
  - Morgen-Erinnerung (Tag der Abfuhr)
  - TTS-Ansagen + Persistent Notifications
  - LLM-Kontext-Injection (Styx weiß wann welcher Müll abgeholt wird)
  - Forwarding an Core Addon
- **Birthday Reminder Module**: Kalender-basierte Geburtstags-Erinnerungen
  - Auto-Discovery von Geburtstags-Kalendern
  - Morgen-TTS: "Heute hat [Name] Geburtstag!"
  - 14-Tage Vorschau auf kommende Geburtstage
  - Alters-Erkennung aus Event-Titel
  - LLM-Kontext für Geburtstagsfragen
- **Config Flow**: 12 neue Einstellungen (Waste + Birthday, jeweils Entities, TTS, Uhrzeiten)
- **Translations**: EN + DE für alle neuen Config-Keys
- Versions-Sync: manifest.json auf 3.2.0

## [3.0.0] - 2026-02-19

### Kollektive Intelligenz — Federated Learning + A/B Testing

- **Federated Learning Integration**: Cross-Home Pattern-Sharing Entities
- **A/B Testing Support**: Experiment-Tracking fuer Automation-Varianten
- **Pattern Library**: Kollektiv gelernte Muster sichtbar in Dashboard
- **Versions-Sync**: manifest.json auf 3.0.0 synchronisiert mit Core

## [2.2.0] - 2026-02-19

### Praediktive Intelligenz — Ankunft + Energie

- **Prediction Entities**: Arrival Forecast, Energy Optimization Sensors
- **Energiepreis-Integration**: Tibber/aWATTar Sensor-Support
- **Versions-Sync**: manifest.json auf 2.2.0

## [2.1.0] - 2026-02-19

### Erklaerbarkeit + Multi-User

- **Explainability Entities**: "Warum?"-Sensor fuer Vorschlaege
- **Multi-User Profile Entities**: Pro-Person Praeferenz-Sensoren
- **Versions-Sync**: manifest.json auf 2.1.0

## [2.0.0] - 2026-02-19

### Native HA Integration — Lovelace Cards + Conversation Agent

- **3 Native Lovelace Cards**:
  - `styx-brain-card.js`: Brain Graph Visualisierung mit Force-Directed Layout
  - `styx-mood-card.js`: Mood Circular Gauges (Comfort/Joy/Frugality)
  - `styx-habitus-card.js`: Top-5 Pattern-Liste mit Confidence-Badges
- **HA Conversation Agent**: `StyxConversationAgent` in `conversation.py`,
  nativ in HA Assist Pipeline, Proxy zu Core `/v1/chat/completions`
- **Versions-Sync**: manifest.json auf 2.0.0

## [1.3.0] - 2026-02-19

### Module Control — Echte Backend-Steuerung

- **Versions-Sync**: manifest.json auf 1.3.0 synchronisiert mit Core v1.3.0
- **Module Control**: Dashboard-Toggles steuern jetzt echtes Backend
- **Automation Creator**: Akzeptierte Vorschlaege werden HA-Automationen

## [1.2.0] - 2026-02-19

### Qualitaetsoffensive — Stabile Integration fuer den Livetest

- **Versions-Sync**: manifest.json auf 1.2.0 synchronisiert mit Core Add-on v1.2.0
- **HA Kompatibilitaet**: Vollstaendig kompatibel mit HA 2024.x und 2025.x
- **Keine Breaking Changes**: Config Flow, Sensors, Translations, HACS-Installation
  unveraendert stabil

## [1.1.0] - 2026-02-19

### Styx — Die Verbindung beider Welten

- **Styx Naming in Config Flow**: Zero Config creates "Styx — PilotSuite" entry,
  manual setup includes `assistant_name` field (default: "Styx")
- **Translations**: EN + DE updated with Styx setup titles and descriptions
- **hacs.json**: Name updated to "PilotSuite — Styx"

---

## [1.0.0] - 2026-02-19

### PilotSuite v1.0.0 -- First Full Release

The PilotSuite HACS Integration is now fully installable with zero-config setup.

### Features
- **Zero Config Setup**: One-click installation -- PilotSuite discovers devices
  automatically and improves through conversation. No questions asked.
- **Quick Start Wizard**: Guided 7-step wizard for zone/device configuration
- **50+ Dashboard Cards**: Overview, Brain Graph, Habitus, Mood, Energy, Presence,
  Mobile-responsive, Mesh monitoring, Interactive filters
- **extended_openai_conversation_pilot**: OpenAI-compatible conversation agent
  for HA's Assist pipeline, connecting to PilotSuite Core at localhost:8909
- **23 Core Modules**: Events forwarder, Brain Graph sync, Habitus miner, Mood,
  Energy/Weather/Presence/UniFi/Camera/ML/Voice context, Home Alerts, and more
- **80+ Sensors**: Entity state tracking across all PilotSuite modules
- **Tag System v0.2**: Entity tagging with registry, assignment, and sync

### Breaking Changes
- Version jump from 0.15.2 to 1.0.0
- Default port changed to 8909

---

## [0.15.1] - 2026-02-18

### Features
- **MUPL Integration in Vector Client**
  - Vector Store Client nutzt jetzt echte Preferenzdaten von MUPL
  - `get_user_similarity_recommendations()` liefert reale User-Präferenzen
  - Fallback zu similarity-basierten Hints wenn MUPL nicht verfügbar

### Fixed
- **Logging**: print() → logger in transaction_log.py (Core Add-on)

---

## [0.14.2] - 2026-02-18

### Performance
- **TTLCache Memory Leak Fix:** Cleanup expired entries on every set()
- **Pydantic Models:** api/models.py for API validation (395 lines)

---

## [0.14.1] - 2026-02-18

### Refactored
- **button_debug.py Modularisierung:**
  - Aufteilung in 8 separate Module (brain, core, debug_controls, forwarder, ha_errors, logs, misc)
  - Reduzierung Hauptdatei von 821 auf 60 Zeilen
  - Bessere Wartbarkeit und Übersicht

### Fixed
- **Race Conditions:** asyncio.Lock für Event Forwarder Queue
- **Port-Konflikt:** DEFAULT_PORT auf 8099 (HA Add-on Standard)

---


## [0.14.1-alpha.6] - 2026-02-17

### Added
- **Preference Input Card:** Neue Card für delegation workflows
  - preference_input_card.py: Card Entity für preference workflows
  - Feature: Preference input workflows, conflict resolution UI, schedule automation
  - Card Type: Diagnostic Card mit state attributes

### Tests
- Syntax-Check: ✅ preference_input_card.py kompiliert
- Preference Input Card: ✅ Created and integrated

---

## [0.14.1-alpha.5] - 2026-02-17
