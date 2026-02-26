# Release Notes - PilotSuite Styx HA

> Hinweis: Fuer die vollstaendige Historie siehe `CHANGELOG.md`.

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
