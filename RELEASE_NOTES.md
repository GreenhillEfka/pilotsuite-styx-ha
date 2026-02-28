# Release Notes - PilotSuite Styx HA

> Hinweis: Fuer die vollstaendige Historie siehe `CHANGELOG.md`.

## v11.2.0 (2026-02-28)

- Paired Release: Core `v11.2.0`.
- Dashboard UX auf Live-Entitaeten erweitert:
  - Habitus: CO2/Lärm im Zonen-Header + Luftqualitaetsverlauf.
  - Hausverwaltung: dynamische Sektionen fuer Energie/Heizung/CO2/Lärm/Medien/Sicherheit/Netzwerk/Wetter.
  - Hausverwaltung: kompakte Zonenuebersicht mit rollenbasierter Verdichtung.
- Infrastruktur-Erkennung verbessert (`media`, `co2`, `noise` + dedup/sort).
- Neuer CI-Gate: `docs-freshness` Workflow + `scripts/check_docs_freshness.py`.
- Kern-Dokumente auf Release-Baseline `11.2.0` synchronisiert.

## v10.1.5 (2026-02-27)

- Paired Release: Core `v10.1.5` (Habitus Miner konfigurierbar + mining repariert, native HA Shopping List, Network-T0 health, entities list endpoint, Chat-History Persistenz).

## v10.1.4 (2026-02-27)

- Zero-config: Dashboards + Events werden ab jetzt out-of-the-box aktiviert (Entity-Profile `full`, Forwarder enabled, YAML-Dashboards enabled).
- Dashboard UX: Habitus-Zonen YAML ist nie mehr leer (Starter-View + Buttons).
- Core Pipeline: Waste + Birthdays werden HA → Core gepusht (Haushalt-Tab bekommt echte Daten).
- Button: **PilotSuite reload dashboards**.
- Fix: Calendar Sensor (`calendar.get_events`) stabilisiert.
- Paired Release: Core `v10.1.4`

## v10.1.3 (2026-02-26)

- Core/HA Versionschutz: Major/Minor Mismatch wird als Repairs-Hinweis angezeigt.
- Contract-Tests fuer wichtige Core Endpoint-Pfade.
- Paired Release: Core `v10.1.3`

## v10.1.2 (2026-02-26)

- HA Best Practice: `single_config_entry` im Manifest aktiviert (verhindert multiple Config-Entries/Duplikate).
- Paired Release: Core `v10.1.2`

## v10.1.1 (2026-02-26)

- Fix: Versionsync/Metadaten konsolidiert (Repo + Integration) und Status/Doku nachgezogen.
- Paired Release: Core `v10.1.1`

## v10.1.0 (2026-02-26)

- Fix: Sensor-Datenpfade bereinigt, fehlende Sensoren ergänzt, Coordinator vervollständigt.
- Paired Release: Core `v10.1.0`

---

## v9.0.0 (2026-02-26)

**Version:** 9.0.0
**Date:** 2026-02-26
**Tag:** `v9.0.0`
**Branch:** main (HA/HACS konform)

## Highlights

v9.0.0 ist ein Architektur-Overhaul mit zentralem EventBus, bidirektionaler Zonensynchronisation, automatischem Tag-System und suchbaren Entity-Dropdowns.

### EventBus Architecture
- Zentraler Thread-safe pub/sub EventBus fuer Inter-Modul-Kommunikation.
- Topics: `zone.*`, `mood.*`, `neuron.*`, `candidate.*`, `graph.*`, `event.*`.
- Wildcard-Subscriptions, Event-History, Metriken.

### Bidirektionale Zone Sync
- Neues `ZoneSyncModule` synchronisiert Habituszonen zwischen HA und Core.
- Hash-basierte Deduplizierung verhindert unnoetige Syncs.
- Neuer API-Endpunkt `/api/v1/habitus/zones/sync` mit Fallback auf Legacy.

### Automation Adoption
- Neues `AutomationAdoptionModule` konvertiert Core-Vorschlaege in HA-Automationen.
- Services: `adopt_suggestion`, `dismiss_suggestion`.

### Tag-System v2
- Dual-Layer: Manuell + automatisch (Zone/Styx).
- `async_auto_tag_zone_entities()` taggt Entities automatisch mit Zonenzugehoerigkeit.
- Rollenbasierte Farben pro Zone (Kueche=Orange, Bad=Cyan, Schlafzimmer=Indigo, ...).

### Habitus Zone Dashboard Card
- Lovelace-Card-Generator fuer Zonenuebersicht mit Mood-Gauges.
- Komfort/Freude/Sparsamkeit als Balkendarstellung pro Zone.
- News/Warnungen, Household Quick Actions (Alle Lichter aus, Alles sichern, Gute Nacht).

### Entity Search
- Suchbare Entity-Dropdowns via Core API (`/api/v1/entities/search`).
- Domain-Filter, Area-Filter, sortierte Ergebnisse.

## Neue Module
| Modul | Datei | Funktion |
|-------|-------|----------|
| `CoordinatorModule` | `core/modules/coordinator_module.py` | Coordinator Lifecycle |
| `AutomationAdoptionModule` | `core/modules/automation_adoption.py` | Vorschlaege → Automationen |
| `ZoneSyncModule` | `core/modules/zone_sync_module.py` | Bidirektionale Zonensync |

## Version Sync
- `custom_components/ai_home_copilot/manifest.json`: `9.0.0`
- Paired with Core `v9.0.0`

## Validation
```bash
cd pilotsuite-styx-ha
python3 -c "import json; json.load(open('custom_components/ai_home_copilot/strings.json'))"
python3 -m py_compile custom_components/ai_home_copilot/__init__.py
python3 -m py_compile custom_components/ai_home_copilot/config_zones_flow.py
python3 -m py_compile custom_components/ai_home_copilot/core/modules/entity_tags_module.py
python3 -m py_compile custom_components/ai_home_copilot/core/modules/zone_sync_module.py
python3 -m py_compile custom_components/ai_home_copilot/core/modules/automation_adoption.py
python3 -m py_compile custom_components/ai_home_copilot/core/modules/coordinator_module.py
```

---

**PilotSuite Styx HA v9.0.0**
