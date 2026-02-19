# PilotSuite HACS Integration -- Benutzerhandbuch

> Version 3.8.1 | Letzte Aktualisierung: Februar 2026

Dieses Handbuch beschreibt die vollstaendige Einrichtung und Nutzung der PilotSuite HACS Integration fuer Home Assistant. Die Integration verbindet sich mit dem [Core Add-on](https://github.com/GreenhillEfka/Home-Assistant-Copilot) (Port 8909) und stellt 94+ Sensoren, 28 Module und Dashboard Cards in Home Assistant bereit.

**Voraussetzung:** Das Core Add-on muss installiert und gestartet sein, bevor die Integration konfiguriert wird.

---

## Inhaltsverzeichnis

1. [Setup](#1-setup)
2. [Habituszonen](#2-habituszonen)
3. [28 Module](#3-28-module)
4. [94+ Sensoren](#4-94-sensoren)
5. [Neural System](#5-neural-system)
6. [Learning Pipeline](#6-learning-pipeline)
7. [Events Forwarder](#7-events-forwarder)
8. [Dashboard](#8-dashboard)
9. [Entity Tags](#9-entity-tags)
10. [Troubleshooting](#10-troubleshooting)
11. [Privacy](#11-privacy)

---

## 1. Setup

### HACS Installation

1. [HACS](https://hacs.xyz) oeffnen
2. **Integrations** -- Menue -- **Custom repositories**
3. URL eingeben: `https://github.com/GreenhillEfka/ai-home-copilot-ha` -- Typ: **Integration**
4. **PilotSuite** installieren und Home Assistant **neustarten**

### Drei Setup-Pfade

Nach der Installation wird die Integration unter **Settings -- Devices & services -- Add integration -- PilotSuite** eingerichtet. Es stehen drei Pfade zur Auswahl:

| Pfad | Beschreibung | Empfohlen fuer |
|------|-------------|----------------|
| **Zero Config** | Sofortstart mit Standardwerten. Styx erkennt Geraete automatisch und fragt spaeter per Gespraech nach Verbesserungen. | Erstbenutzer, schneller Test |
| **Quick Start** | Gefuehrter Wizard (~2 Min). Optionale Auto-Discovery, Zonen-Auswahl, Media-Player-Zuweisung, Feature-Auswahl, Netzwerk-Konfiguration. | Die meisten Benutzer |
| **Manual Setup** | Vollstaendige manuelle Konfiguration aller Felder. | Erfahrene Benutzer, spezielle Netzwerk-Setups |

### Konfigurationsfelder

| Feld | Beschreibung | Standard |
|------|-------------|----------|
| `assistant_name` | Anzeigename des Assistenten | `Styx` |
| `host` | Hostname oder IP-Adresse des Core Add-ons | `homeassistant.local` |
| `port` | Port des Core Add-ons | `8909` |
| `token` | Authentifizierungs-Token (leer = kein Token, fuer Ersteinrichtung) | (leer) |
| `test_light_entity_id` | Optionale Licht-Entity fuer Funktionstest | (leer) |

### Quick Start Wizard -- Schritte

1. **Discovery**: Auto-Discovery aktivieren (scannt kompatible Geraete)
2. **Zones**: Vorgeschlagene Zonen aus HA Areas auswaehlen
3. **Zone Entities**: Entities pro Zone zuweisen (Motion, Lights, Sensoren, Media)
4. **Entities**: Media-Player konfigurieren (Musik + TV)
5. **Features**: Gewuenschte Module aktivieren
6. **Network**: Host, Port, Token eingeben
7. **Review**: Zusammenfassung pruefen und bestaetigen

### Nachtraegliche Konfiguration

Alle Einstellungen koennen jederzeit ueber **Settings -- Integrations -- PilotSuite -- Configure** geaendert werden. Der Options Flow bietet ein Hauptmenue mit den Bereichen:

- **Settings** -- Alle Konfigurationsfelder (Netzwerk, Module, Forwarder, Debug)
- **Habitus zones** -- Zonen erstellen/bearbeiten/loeschen, Dashboard generieren, Bulk-Edit
- **Entity Tags** -- Tags erstellen/bearbeiten/loeschen
- **Neurons** -- Neural System konfigurieren (Context, State, Mood Entities)
- **Backup/Restore** -- Konfigurations-Snapshots

---

## 2. Habituszonen

Habituszonen sind **unabhaengig von HA Areas**. Sie definieren kuratierte Raeume, in denen PilotSuite zonenspezifische Muster lernt und passende Automatisierungen vorschlaegt.

### Anforderungen pro Zone

Jede Habituszone benoetigt mindestens:

- **1 Motion/Praesenz-Entity** (binary_sensor oder sensor mit device_class motion/presence/occupancy)
- **1 Licht-Entity** (light.*)

Ohne diese beiden Pflicht-Entities kann keine Zone angelegt werden.

### Zonentypen

| Typ | Hierarchie-Level | Beschreibung |
|-----|-----------------|-------------|
| `floor` | 0 | Etage (EG, OG, UG) |
| `area` | 1 | Bereich (z.B. Wohnbereich, Schlafbereich) |
| `room` | 2 (Standard) | Einzelner Raum |
| `outdoor` | 3 | Aussenbereich |

### Entity-Rollen

Jede Zone ordnet ihre Entities in Rollen ein:

| Rolle | Beschreibung | Beispiel |
|-------|-------------|---------|
| `motion` | Bewegungs-/Praesenzmelder (Pflicht) | `binary_sensor.wohnzimmer_motion` |
| `lights` | Lichtsteuerung (Pflicht) | `light.wohnzimmer_decke` |
| `brightness` / `illuminance` | Helligkeitssensor | `sensor.wohnzimmer_lux` |
| `temperature` | Temperatursensor | `sensor.wohnzimmer_temperatur` |
| `humidity` | Luftfeuchte | `sensor.wohnzimmer_humidity` |
| `co2` | CO2-Sensor | `sensor.wohnzimmer_co2` |
| `heating` / `climate` | Heizung/Klima | `climate.wohnzimmer` |
| `cover` | Jalousien/Rollos | `cover.wohnzimmer_rollo` |
| `door` | Tuersensor | `binary_sensor.wohnzimmer_tuer` |
| `window` | Fenstersensor | `binary_sensor.wohnzimmer_fenster` |
| `lock` | Schloss | `lock.haustuer` |
| `media` | Media-Player | `media_player.wohnzimmer_sonos` |
| `power` / `energy` | Strom-/Energiemessung | `sensor.wohnzimmer_strom` |
| `noise` | Laermpegel | `sensor.wohnzimmer_noise` |
| `pressure` | Luftdruck | `sensor.wohnzimmer_druck` |
| `other` | Sonstige Entities | beliebig |

Rollen-Aliase werden automatisch aufgeloest (z.B. `presence` wird zu `motion`, `rollo` wird zu `cover`, `luftfeuchte` wird zu `humidity`).

### CRUD ueber Options Flow

Unter **Settings -- Integrations -- PilotSuite -- Configure -- Habitus zones**:

- **Create zone**: Zone-ID, Name, Motion-Entity, Light-Entities, optionale Entities eingeben
- **Edit zone**: Bestehende Zone aus Dropdown waehlen und Felder aendern
- **Delete zone**: Zone aus Dropdown waehlen und loeschen

### Bulk-Edit (YAML/JSON)

Fuer groessere Anpassungen steht der **Bulk Edit** zur Verfuegung. Hier kann die gesamte Zonen-Konfiguration als YAML oder JSON eingefuegt werden. Das System validiert die Eingabe und zeigt Fehler an.

Beispiel (YAML):

```yaml
- id: zone:wohnzimmer
  name: Wohnzimmer
  entities:
    motion:
      - binary_sensor.wohnzimmer_motion
    lights:
      - light.wohnzimmer_decke
      - light.wohnzimmer_stehlampe
    temperature:
      - sensor.wohnzimmer_temperatur
    humidity:
      - sensor.wohnzimmer_humidity
    media:
      - media_player.wohnzimmer_sonos

- id: zone:schlafzimmer
  name: Schlafzimmer
  entities:
    motion:
      - binary_sensor.schlafzimmer_motion
    lights:
      - light.schlafzimmer_decke
    cover:
      - cover.schlafzimmer_rollo
```

Alternativ mit `entity_ids` (Flachliste) statt kategorisierter `entities`-Map:

```yaml
- id: zone:kueche
  name: Kueche
  entity_ids:
    - binary_sensor.kueche_motion
    - light.kueche_decke
    - sensor.kueche_temperatur
```

Es wird auch JSON akzeptiert, und das Format `{"zones": [...]}` ist ebenfalls gueltig.

### Zonenhierarchie und Konflikte

Zonen koennen eine Eltern-Kind-Beziehung haben (`parent_zone_id`, `child_zone_ids`). Bei ueberlappenden Entities zwischen aktiven Zonen greift die Konfliktaufloesung:

1. **Hierarchy**: Spezifischere Zonen (Kinder) ueberschreiben allgemeinere (Eltern)
2. **Priority**: Hoeherer Prioritaetswert gewinnt (0=niedrig, 10=hoch)
3. **User Prompt**: Benutzer wird zur Aufloesung aufgefordert

### Zonen-States

Jede Zone hat einen Zustand: `idle`, `active`, `transitioning`, `disabled`, `error`. States werden persistent ueber HA-Neustarts gespeichert.

---

## 3. 28 Module

Alle Module implementieren das `CopilotModule`-Interface und werden ueber die Runtime-Registry verwaltet. Jedes Modul hat einen standardisierten Lifecycle (`async_setup_entry`, `async_unload_entry`, `async_reload_entry`).

| Nr | Modul | Registry-Name | Funktion |
|----|-------|--------------|----------|
| 1 | LegacyModule | `legacy` | Basis-Integration: Coordinator, Webhook, Blueprints, Plattformen (sensor, button, etc.) |
| 2 | PerformanceScalingModule | `performance_scaling` | Performance-Guardrails, Backoff-Limits, Concurrency-Guards |
| 3 | EventsForwarderModule | `events_forwarder` | HA-Events an Core senden (batched, PII-redacted, persistent queue, idempotent) |
| 4 | DevSurfaceModule | `dev_surface` | Debug-Steuerung, Error-Registry, Debug-Timer (30min), Log-Level-Verwaltung |
| 5 | HabitusMinerModule | `habitus_miner` | A-zu-B Pattern-Discovery, Association Rules, Zone-basiertes Mining |
| 6 | OpsRunbookModule | `ops_runbook` | Operations-Runbook: haeufige Probleme und Loesungsanleitungen |
| 7 | UniFiModule | `unifi_module` | UniFi-Netzwerkdiagnose: WAN-Qualitaet, Wi-Fi-Roaming, AP-Health |
| 8 | BrainGraphSyncModule | `brain_graph_sync` | Brain Graph Synchronisation mit Core via /api/v1/graph Endpoints |
| 9 | CandidatePollerModule | `candidate_poller` | Vorschlaege vom Core abholen (5min), HA Repairs Issues erstellen, Decisions ruecksynchen |
| 10 | MediaContextModule | `media_zones` | Media-Player Tracking: Musik, TV, Zonen-Zuordnung, Privacy-safe |
| 11 | MoodModule | `mood` | Lokale Mood-Inferenz: Comfort/Joy/Frugality Vektor, Character-Integration |
| 12 | MoodContextModule | `mood_context` | Mood-Consumer: Core Mood API pollen, Zone-Mood-Cache, Suggestion-Suppression |
| 13 | EnergyContextModule | `energy_context` | Energiemonitoring: Verbrauch, Produktion, Anomalien, Load-Shifting |
| 14 | UnifiContextModule | `network` | Netzwerk-Kontext: WAN-Status, Clients, Roaming, Traffic-Baselines |
| 15 | WeatherContextModule | `weather_context` | Wetter-Daten fuer PV-Forecasting und Energieoptimierung |
| 16 | KnowledgeGraphSyncModule | `knowledge_graph_sync` | Knowledge Graph Sync: Entities, Areas, Zones, Tags, Capabilities |
| 17 | MLContextModule | `ml_context` | ML-Pipeline: Anomaly Detection, Habit Prediction, Energy Optimization |
| 18 | CameraContextModule | `camera_context` | Kamera-Events: Motion, Gesichtserkennung, Objekterkennung (lokal) |
| 19 | QuickSearchModule | `quick_search` | Entity-, Automations- und Service-Suche fuer Schnellzugriff |
| 20 | VoiceContextModule | `voice_context` | Sprachsteuerungs-Kontext: Befehle, TTS, Zustandstracking |
| 21 | HomeAlertsModule | `home_alerts` | Kritische Zustandsueberwachung: Batterie, Klima, Praesenz, System |
| 22 | CharacterModule | `character_module` | Persoenlichkeit/Character-Presets: Mood-Gewichtung, Stimmton |
| 23 | WasteReminderModule | `waste_reminder` | Abfuhr-Erinnerungen: Abend + Morgen, TTS, Persistent Notifications |
| 24 | BirthdayReminderModule | `birthday_reminder` | Geburtstags-Erinnerungen: Kalender-Scan, TTS, 14-Tage-Vorschau |
| 25 | EntityTagsModule | `entity_tags` | Entity-Tagging: Manuelle + Auto-Tags ("Styx"), Modul-Abfragen |
| 26 | PersonTrackingModule | `person_tracking` | Personen-Tracking: Wer ist zuhause, Ankunft/Abreise-Historie |
| 27 | FrigateBridgeModule | `frigate_bridge` | Frigate NVR Bridge: Person/Motion Detection Events weiterleiten |
| 28 | SceneModule | `scene_module` | Szenen-Management: Zonen-Szenen speichern/lernen/vorschlagen |
| -- | HomeKitBridgeModule | `homekit_bridge` | HomeKit-Bridge: Habitus-Zonen als HomeKit-kompatible Bridge |
| -- | CalendarModule | `calendar_module` | Kalender-Integration: HA calendar.* Entities, Events fuer LLM-Kontext |

Zusaetzlich werden folgende Module separat gestartet (nicht ueber die Runtime-Registry):

- **UserPreferenceModule**: Multi-User Preference Learning (einzeln, per Config-Option)
- **MultiUserPreferenceModule (MUPL)**: Erweitertes Multi-User Learning (opt-in)
- **ZoneDetector**: Proaktive Zonen-Eintritts-Erkennung und Weiterleitung an Core

---

## 4. 94+ Sensoren

Alle Sensoren verwenden den Entity-ID Prefix `sensor.ai_home_copilot_*`. Die `unique_id` folgt dem Schema `ai_home_copilot_{feature}_{name}`.

### Mood-Sensoren

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_copilot_mood` | Aktueller Mood (comfort/joy/frugality) |
| `sensor.ai_copilot_mood_confidence` | Confidence-Wert des Mood-Signals |
| `sensor.ai_copilot_neuron_activity` | Neuronale Aktivitaet (aggregiert) |
| `sensor.ai_home_copilot_mood_dashboard` | Mood Dashboard JSON |
| `sensor.ai_home_copilot_mood_history` | Mood-Verlauf |
| `sensor.ai_home_copilot_mood_explanation` | Mood-Erklaerung (Beitragende Neuronen) |

### Neuronen-Sensoren (14)

| Entity-ID Pattern | Neuron | Beschreibung |
|-------------------|--------|-------------|
| `sensor.ai_home_copilot_presence_room` | Presence.Room | Aktiver Raum basierend auf Motion-Entities |
| `sensor.ai_home_copilot_presence_person` | Presence.Person | Erkannte Personen im Haushalt |
| `sensor.ai_home_copilot_activity_level` | Activity.Level | Aktivitaetsniveau (low/medium/high) |
| `sensor.ai_home_copilot_activity_stillness` | Activity.Stillness | Stillstandsdauer |
| `sensor.ai_home_copilot_time_of_day` | Time.OfDay | Tageszeit-Segment (morning/noon/afternoon/evening/night) |
| `sensor.ai_home_copilot_day_type` | Day.Type | Tagestyp (workday/weekend/holiday) |
| `sensor.ai_home_copilot_routine_stability` | Routine.Stability | Stabilitaet der Tagesroutine |
| `sensor.ai_home_copilot_light_level` | Environment.Light | Helligkeitsniveau |
| `sensor.ai_home_copilot_noise_level` | Environment.Noise | Laermpegel |
| `sensor.ai_home_copilot_weather_context` | Weather.Context | Wetter-Kontext (klar/bewoelkt/regen/etc.) |
| `sensor.ai_home_copilot_calendar_load` | Calendar.Load | Kalender-Auslastung (frei/normal/voll) |
| `sensor.ai_home_copilot_attention_load` | Cognitive.Attention | Aufmerksamkeitsbelastung |
| `sensor.ai_home_copilot_stress_proxy` | Cognitive.Stress | Stress-Proxy (abgeleitet aus Aktivitaet, Kalender, etc.) |
| `sensor.ai_home_copilot_energy_proxy` | Energy.Proxy | Energieverbrauchs-Proxy |
| `sensor.ai_home_copilot_media_activity` | Media.Activity | Medien-Nutzung (idle/playing/paused) |
| `sensor.ai_home_copilot_media_intensity` | Media.Intensity | Medien-Intensitaet |

### Habitus-Sensoren

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_home_copilot_habitus_zones_v2_count` | Anzahl konfigurierter Habituszonen |
| `sensor.ai_home_copilot_habitus_zones_v2_states` | Zonen-States (idle/active/etc.) |
| `sensor.ai_home_copilot_habitus_zones_v2_health` | Zonen-Gesundheit |
| `sensor.ai_home_copilot_habitus_miner_rule_count` | Anzahl entdeckter Association Rules |
| `sensor.ai_home_copilot_habitus_miner_status` | Mining-Status (idle/mining/ready) |
| `sensor.ai_home_copilot_habitus_miner_top_rule` | Staerkste entdeckte Regel |
| `sensor.ai_home_copilot_*_zone_avg_*` | Zonen-Durchschnittswerte (Temperatur, Luftfeuchte, etc.) |

### Energy-Sensoren

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_home_copilot_energy_insight` | Energie-Einblick (ML-basiert) |
| `sensor.ai_home_copilot_energy_recommendation` | Energie-Empfehlung |
| `sensor.ai_home_copilot_energy_proxy` | Energieverbrauchs-Proxy |

### Media-Sensoren

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_home_copilot_music_now_playing` | Aktuell spielender Titel |
| `sensor.ai_home_copilot_music_primary_area` | Bereich mit aktiver Musik |
| `sensor.ai_home_copilot_music_active_count` | Anzahl aktiver Musik-Player |
| `sensor.ai_home_copilot_tv_primary_area` | Bereich mit aktivem TV |
| `sensor.ai_home_copilot_tv_source` | Aktive TV-Quelle |
| `sensor.ai_home_copilot_tv_active_count` | Anzahl aktiver TV-Player |
| `sensor.ai_home_copilot_media_v2_active_mode` | Aktiver Media-Modus (v2) |
| `sensor.ai_home_copilot_media_v2_active_target` | Aktives Media-Ziel (v2) |
| `sensor.ai_home_copilot_media_v2_active_zone` | Aktive Media-Zone (v2) |

### Brain Graph / Knowledge Graph

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_copilot_neuron_dashboard` | Neuron Dashboard JSON (alle Neuron-States) |
| `sensor.ai_copilot_mood_history` | Mood-Historie |
| `sensor.ai_copilot_suggestion` | Aktuelle Vorschlaege |

### Calendar / Waste / Birthday

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_home_copilot_calendar_context` | Kalender-Kontext (Events, Focus/Social Weight) |
| `sensor.ai_home_copilot_calendar` | Integrierte HA-Kalender |
| `sensor.ai_home_copilot_waste_next_collection` | Naechste Abfuhr (Typ, Tage bis, Datum) |
| `sensor.ai_home_copilot_waste_today_count` | Anzahl Abfuhren heute |
| `sensor.ai_home_copilot_birthday_today_count` | Geburtstage heute |
| `sensor.ai_home_copilot_birthday_next` | Naechster Geburtstag (Name, Tage bis, Alter) |

### ML / Anomaly / Prediction

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_home_copilot_anomaly_alert` | Aktiver Anomalie-Alarm |
| `sensor.ai_home_copilot_alert_history` | Alarm-Historie |
| `sensor.ai_home_copilot_habit_learning` | Gelernte Gewohnheiten |
| `sensor.ai_home_copilot_habit_prediction` | Habit-Vorhersage |
| `sensor.ai_home_copilot_sequence_prediction` | Sequenz-Vorhersage |
| `sensor.ai_home_copilot_predictive_automation` | Vorgeschlagene Automatisierung |
| `sensor.ai_home_copilot_predictive_automation_details` | Details zur Vorhersage |

### System / Health

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_home_copilot_version` | Installierte Version |
| `sensor.ai_home_copilot_core_api_v1_status` | Core API Status (online/offline) |
| `sensor.ai_home_copilot_pipeline_health` | Pipeline-Gesundheit |
| `sensor.ai_home_copilot_debug_mode` | Aktueller Debug-Modus (off/light/full) |
| `sensor.ai_home_copilot_entity_count` | Anzahl verwalteter Entities |
| `sensor.ai_home_copilot_sqlite_db_size` | SQLite-Datenbankgroesse |
| `sensor.ai_home_copilot_inventory_last_run` | Letzter Inventar-Scan |

### Mesh / Netzwerk

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_home_copilot_zwave_network_health` | Z-Wave Netzwerk-Gesundheit |
| `sensor.ai_home_copilot_zwave_devices_online` | Z-Wave Geraete online |
| `sensor.ai_home_copilot_zwave_battery_overview` | Z-Wave Batterie-Uebersicht |
| `sensor.ai_home_copilot_zigbee_network_health` | Zigbee Netzwerk-Gesundheit |
| `sensor.ai_home_copilot_zigbee_devices_online` | Zigbee Geraete online |
| `sensor.ai_home_copilot_zigbee_battery_overview` | Zigbee Batterie-Uebersicht |
| `sensor.ai_home_copilot_mesh_network_overview` | Mesh-Netzwerk Uebersicht |
| `sensor.ai_home_copilot_network_health` | UniFi Netzwerk-Gesundheit |

### Events Forwarder

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_home_copilot_forwarder_queue_depth` | Aktuelle Queue-Tiefe |
| `sensor.ai_home_copilot_forwarder_dropped_total` | Verworfene Events (gesamt) |
| `sensor.ai_home_copilot_forwarder_error_streak` | Fehler-Serie (aktuelle) |

### Home Alerts

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_home_copilot_home_alerts_count` | Anzahl aktiver Alerts |
| `sensor.ai_home_copilot_home_health_score` | Haus-Gesundheits-Score (0-100) |
| `sensor.ai_home_copilot_home_alerts_battery` | Batterie-Warnungen |
| `sensor.ai_home_copilot_home_alerts_climate` | Klima-Abweichungen |
| `sensor.ai_home_copilot_home_alerts_presence` | Praesenz-Aenderungen |
| `sensor.ai_home_copilot_home_alerts_system` | System-Warnungen |

### Voice / Camera / Weitere

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_copilot_voice_context` | Voice-Kontext (Sprachsteuerung) |
| `sensor.ai_copilot_voice_prompt` | Aktueller Voice-Prompt |
| `sensor.ai_home_copilot_camera_motion_history` | Kamera Motion-Historie |
| `sensor.ai_home_copilot_camera_presence_history` | Kamera Praesenz-Historie |
| `sensor.ai_home_copilot_camera_activity_history` | Kamera Aktivitaets-Historie |
| `sensor.ai_home_copilot_camera_zone_activity` | Kamera Zonen-Aktivitaet |
| `sensor.ai_home_copilot_character_preset` | Aktives Character-Preset |
| `sensor.ai_home_copilot_entity_tags` | Anzahl Entity-Tags |
| `sensor.ai_home_copilot_persons_home` | Personen zuhause |
| `sensor.ai_home_copilot_frigate_cameras` | Erkannte Frigate-Kameras |
| `sensor.ai_home_copilot_zone_scenes` | Gespeicherte Zonen-Szenen |
| `sensor.ai_home_copilot_homekit_bridge` | HomeKit-exponierte Zonen |
| `sensor.ai_home_copilot_mobile_dashboard` | Mobile Dashboard Card-Daten |

### Inspector-Sensoren (Debug)

| Entity-ID Pattern | Beschreibung |
|-------------------|-------------|
| `sensor.ai_home_copilot_inspector_zones` | Habitus Zones interner State |
| `sensor.ai_home_copilot_inspector_tags` | Active Tags interner State |
| `sensor.ai_home_copilot_inspector_character` | Character Profile interner State |
| `sensor.ai_home_copilot_inspector_mood` | Current Mood interner State |

---

## 5. Neural System

Das Neural System besteht aus **14 Neuronen**, die den Zustand des Haushalts in Echtzeit bewerten. Die Neuronen speisen den Mood-Vektor (Comfort, Joy, Frugality) und beeinflussen Vorschlaege und Automatisierungen.

### Die 14 Neuronen

| Nr | Neuron | Kategorie | Was es misst |
|----|--------|-----------|-------------|
| 1 | Time.OfDay | Zeit | Tageszeit-Segment (morning/noon/afternoon/evening/night) |
| 2 | Day.Type | Zeit | Wochentag-Typ (workday/weekend/holiday) |
| 3 | Routine.Stability | Zeit | Stabilitaet der Tagesroutine im Vergleich zu Durchschnittswerten |
| 4 | Calendar.Load | Kalender | Kalender-Auslastung (Termine naechste 24h) |
| 5 | Attention.Load | Kognitiv | Aufmerksamkeitsbelastung (abgeleitet aus Kalender + Aktivitaet) |
| 6 | Stress.Proxy | Kognitiv | Stress-Proxy (Kalender-Dichte + Aktivitaetsniveau + Tageszeit) |
| 7 | Presence.Room | Praesenz | Aktiver Raum basierend auf Motion-Entities aller Zonen |
| 8 | Presence.Person | Praesenz | Wer ist zuhause (person.*/device_tracker.*) |
| 9 | Energy.Proxy | Energie | Energieverbrauch relativ zur Baseline |
| 10 | Weather.Context | Wetter | Aktuelles Wetter aus weather.* Entities |
| 11 | Environment.Light | Umwelt | Helligkeitsniveau aus Helligkeitssensoren |
| 12 | Environment.Noise | Umwelt | Laermpegel aus Geraeuschsensoren |
| 13 | Activity.Level | Aktivitaet | Gesamtaktivitaet (low/medium/high basierend auf State-Aenderungen) |
| 14 | Activity.Stillness | Aktivitaet | Zeitraum ohne erkannte Bewegung/Aktivitaet |
| -- | Media.Activity | Media | Medien-Nutzung (idle/playing/paused) |
| -- | Media.Intensity | Media | Medien-Intensitaet (abgeleitet aus Typ + Lautstaerke) |

### Konfiguration ueber Options Flow

Unter **Settings -- Integrations -- PilotSuite -- Configure -- Neurons**:

| Einstellung | Beschreibung | Standard |
|------------|-------------|----------|
| `neuron_enabled` | Neural System ein/aus | `true` |
| `neuron_evaluation_interval` | Auswertungsintervall in Sekunden | `60` |
| `neuron_context_entities` | Entity-IDs fuer Kontext-Neuronen (CSV) | (leer) |
| `neuron_state_entities` | Entity-IDs fuer State-Neuronen (CSV) | (leer) |
| `neuron_mood_entities` | Entity-IDs fuer Mood-Neuronen (CSV) | (leer) |

### Mood-Vektor

Die 14 Neuronen werden zu einem 3-dimensionalen Mood-Vektor aggregiert:

- **Comfort**: Raumtemperatur, Helligkeit, Praesenz, Routine-Stabilitaet
- **Joy**: Medien-Aktivitaet, Soziale Events, Wetter
- **Frugality**: Energieverbrauch, Kosten-Proxy

Der Mood-Vektor beeinflusst direkt, welche Vorschlaege das System macht. Beispiel: Waehrend Entertainment-Mood werden keine Energiespar-Vorschlaege angezeigt.

---

## 6. Learning Pipeline

Die Learning Pipeline entdeckt Verhaltensmuster und verwandelt sie in Automatisierungsvorschlaege.

### Kreislauf

```
1. Pattern Discovery     Habitus Miner beobachtet Events in Zonen
        |                (A-zu-B Muster: "Wenn X, dann Y")
        v
2. Suggestion            Entdeckte Regeln werden als Candidates
        |                dem CandidatePoller uebergeben
        v
3. Blueprint             Core generiert HA Blueprint aus dem Pattern
        |                (a_to_b_safe.yaml wird installiert)
        v
4. Automation            Benutzer akzeptiert/verwirft im Repairs UI
                         Bei Annahme: HA Automation erstellt
```

### Habitus Miner

Der Habitus Miner beobachtet HA Events innerhalb konfigurierter Zonen und entdeckt Association Rules:

- **Support**: Wie oft tritt das Muster auf
- **Confidence**: Wie zuverlaessig ist die Vorhersage
- **Lift**: Wie stark ist der Zusammenhang (>1 = staerker als Zufall)

Entdeckte Regeln und der Event-Buffer werden persistent gespeichert (ueberlebt Neustarts). Der Buffer wird alle 5 Minuten und beim Entladen gespeichert.

### Candidate Poller

Pollt den Core alle 5 Minuten auf `GET /api/v1/candidates?state=pending`. Fuer jeden pending Candidate wird ein HA Repairs Issue erstellt. Benutzer-Entscheidungen (akzeptiert/abgelehnt/zurueckgestellt) werden an den Core zurueck-synchonisiert.

Rate Limiting und Exponential Backoff schuetzen vor Ueberlastung.

### 3-Tier Autonomie

Die Autonomiestufe bestimmt, wie PilotSuite mit entdeckten Patterns umgeht:

| Stufe | Verhalten |
|-------|----------|
| **active** | Entdeckte Patterns werden automatisch als Automationen angewendet. Sowohl Module als auch Vorschlaege werden ohne Rueckfrage aktiviert. |
| **learning** (Standard) | Patterns werden als Vorschlaege im Repairs UI angezeigt. Der Benutzer entscheidet ueber Annahme oder Ablehnung. |
| **off** | Keine Pattern-Discovery, keine Vorschlaege. Rein passive Datensammlung. |

### Seed Adapter

Optional koennen externe LLM-generierte Vorschlaege (z.B. von `sensor.ai_automation_suggestions_openai`) als Seed-Candidates eingespeist werden. Konfigurierbar ueber:

- `suggestion_seed_entities`: Entity-IDs der Seed-Quellen
- `seed_allowed_domains` / `seed_blocked_domains`: Domain-Filterung
- `seed_max_offers_per_hour`: Maximal 10 Angebote/Stunde (Standard)
- `seed_min_seconds_between_offers`: Mindestabstand 30 Sekunden

---

## 7. Events Forwarder

Der Events Forwarder sendet HA State-Aenderungen an das Core Add-on im N3-Envelope-Format. Er ist **opt-in** (Standard: aus).

### Aktivierung

Unter **Settings -- Integrations -- PilotSuite -- Configure -- Settings**:

| Einstellung | Standard | Beschreibung |
|------------|----------|-------------|
| `events_forwarder_enabled` | `false` | Forwarder ein/aus |
| `events_forwarder_flush_interval_seconds` | `5` | Flush-Intervall (1-300s) |
| `events_forwarder_max_batch` | `50` | Max Events pro Batch (1-5000) |
| `events_forwarder_forward_call_service` | `false` | Auch call_service Events weiterleiten |
| `events_forwarder_idempotency_ttl_seconds` | `300` | Idempotency-TTL (10-86400s) |

### Batching

Events werden im Speicher gesammelt und alle `flush_interval_seconds` als Batch an den Core gesendet. Jeder Batch enthaelt maximal `max_batch` Events. Bei Fehlern werden Events nicht verloren, sondern im naechsten Zyklus erneut versucht.

### Persistent Queue

Optional kann eine crash-sichere persistente Queue aktiviert werden:

| Einstellung | Standard | Beschreibung |
|------------|----------|-------------|
| `events_forwarder_persistent_queue_enabled` | `false` | Persistente Queue ein/aus |
| `events_forwarder_persistent_queue_max_size` | `500` | Maximale Queue-Groesse (10-50000) |
| `events_forwarder_persistent_queue_flush_interval_seconds` | `5` | Persistente Flush-Intervall |

Events in der persistenten Queue ueberleben HA-Neustarts. Die Queue nutzt HA Storage API mit Groessenbegrenzung.

### Idempotency

Jedes Event erhaelt einen Idempotency-Key basierend auf `event_type:context.id`. Events mit bekanntem Key innerhalb der TTL werden nicht erneut gesendet. Die Standard-TTL betraegt 300 Sekunden (5 Minuten).

### PII-Redaktion

Das N3-Envelope-Format reduziert Attribute auf ein Minimum pro Domain:

- **light**: brightness, color_temp, rgb_color, color_mode
- **climate**: temperature, current_temperature, hvac_action, humidity
- **media_player**: media_content_type, media_title, source, volume_level
- **sensor**: unit_of_measurement, device_class, state_class

Folgende Attribute werden immer entfernt: `entity_picture`, `media_image_url`, `latitude`, `longitude`, `gps_accuracy`, `access_token`, `token`.

Zusaetzlich werden Regex-Pattern fuer Tokens, Keys, Secrets und Passwoerter angewendet.

### Entity-Filterung

| Einstellung | Standard | Beschreibung |
|------------|----------|-------------|
| `events_forwarder_include_habitus_zones` | `true` | Zonen-Entities einschliessen |
| `events_forwarder_include_media_players` | `true` | Media-Player einschliessen |
| `events_forwarder_additional_entities` | (leer) | Zusaetzliche Entity-IDs (CSV) |

### Monitoring

Drei Sensoren ueberwachen den Forwarder-Zustand:

- `sensor.ai_home_copilot_forwarder_queue_depth`: Aktuelle Queue-Tiefe
- `sensor.ai_home_copilot_forwarder_dropped_total`: Verworfene Events
- `sensor.ai_home_copilot_forwarder_error_streak`: Aktive Fehlerserie

---

## 8. Dashboard

### Dashboard-Generierung

Dashboards werden als Lovelace YAML-Dateien generiert. Es gibt zwei Wege:

**Ueber Options Flow:**
- **Settings -- Integrations -- PilotSuite -- Configure -- Habitus zones -- Generate dashboard**
- Erstellt eine YAML-Datei im `ai_home_copilot/` Konfigurationsordner
- **Publish dashboard** kopiert die Datei nach `www/ai_home_copilot/` fuer stabilen Download-URL

**Ueber Buttons:**
- `button.ai_home_copilot_generate_habitus_dashboard`: Dashboard YAML generieren
- `button.ai_home_copilot_download_habitus_dashboard`: Dashboard herunterladen
- `button.ai_home_copilot_generate_pilotsuite_dashboard`: PilotSuite Dashboard generieren
- `button.ai_home_copilot_download_pilotsuite_dashboard`: PilotSuite Dashboard herunterladen

### Dashboard-Inhalt

Das generierte Dashboard enthaelt pro Habituszone:

- **Entities Card**: Alle zugewiesenen Entities mit Zustandsanzeige
- **Status-Cards**: Zonen-State, Aggregierte Durchschnittswerte
- **Aktions-Buttons**: Szenen aktivieren, Zonen-Einstellungen

### Brain Graph Card

Der Brain Graph ist eine interaktive D3.js-Visualisierung des Knowledge Graph. Er zeigt Entities, Zonen, Beziehungen und State-Transitions.

**Generierung:**
- `button.ai_home_copilot_publish_brain_graph_viz`: Statische SVG/HTML Visualisierung
- `button.ai_home_copilot_publish_brain_graph_panel`: Interaktives Panel

Die generierten Dateien werden im `www/ai_home_copilot/` Ordner abgelegt und sind ueber `/local/ai_home_copilot/` erreichbar.

### Mobile Dashboard

Drei spezielle Sensoren liefern Daten fuer mobile Dashboard Cards:

- `sensor.ai_home_copilot_mobile_dashboard`: Mobile-optimierte Uebersicht
- `sensor.ai_home_copilot_mobile_quick_actions`: Schnellzugriff-Aktionen
- `sensor.ai_home_copilot_mobile_entity_grid`: Entity-Grid fuer Mobilansicht

---

## 9. Entity Tags

Entity Tags erlauben benutzerdefinierte Gruppierung von HA Entities unabhaengig von Domains, Areas oder Zonen. Module koennen Tags abfragen, um gezielt Entities zu finden (z.B. "alle Entities mit Tag Licht").

### Vordefinierte Tag-Farben

| Tag-ID | Farbe |
|--------|-------|
| `licht` | Gelb (#fbbf24) |
| `klima` | Gruen (#34d399) |
| `sicherheit` | Rot (#f87171) |
| `energie` | Blau (#60a5fa) |
| `wasser` | Cyan (#22d3ee) |
| `heizung` | Orange (#fb923c) |
| `ueberwachen` | Pink (#f472b6) |
| (andere) | Indigo (#6366f1) |

### Tag-Verwaltung ueber Options Flow

Unter **Settings -- Integrations -- PilotSuite -- Configure -- Entity Tags**:

- **Add tag**: Tag-ID (slug, lowercase), Name, Entity-IDs, Farbe eingeben
- **Edit tag**: Bestehenden Tag aus Liste waehlen, Entities aendern
- **Delete tag**: Tag aus Liste waehlen und loeschen

Tag-IDs muessen dem Format `^[a-z0-9_aeoeuess]+$` entsprechen (lowercase, Ziffern, Unterstriche, Umlaute).

### Auto-Tagging ("Styx")

Das EntityTagsModule vergibt automatisch den Tag `styx` an jede Entity, mit der Styx interagiert. Dieses Auto-Tagging hilft zu erkennen, welche Entities aktiv von PilotSuite genutzt werden.

### Tag in Sensoren

Der Sensor `sensor.ai_home_copilot_entity_tags` zeigt die Gesamtanzahl definierter Tags. In den `extra_state_attributes` findet sich die vollstaendige Tag-Liste mit zugehoerigen Entities.

---

## 10. Troubleshooting

### cannot_connect

**Symptom:** Config Flow zeigt Fehler `cannot_connect` bei der Einrichtung.

**Ursachen und Loesungen:**

| Pruefpunkt | Loesung |
|-----------|---------|
| Core Add-on nicht gestartet | Add-on unter **Settings -- Add-ons** starten |
| Falscher Host | Standard `homeassistant.local` verwenden, oder IP-Adresse des HA-Hosts |
| Falscher Port | Standard `8909` sicherstellen; Core Add-on Konfiguration pruefen |
| Port blockiert | Firewall-Regeln pruefen; Port 8909 muss intern erreichbar sein |
| Token stimmt nicht | Token leer lassen (Ersteinrichtung) oder korrektes Token aus Core-Konfiguration verwenden |

### Modul laedt nicht

**Symptom:** Ein Modul erscheint nicht oder wirft Fehler beim Start.

**Loesungen:**

1. **Logs pruefen**: Unter **Settings -- System -- Logs** nach `ai_home_copilot` filtern
2. **Debug aktivieren**: Options Flow -- Settings -- `debug_level` auf `full` setzen
3. **Modul-Isolation**: Fehlgeschlagene Module werden automatisch uebersprungen und der Rest laedt normal weiter (Isolation per try/except im Runtime)
4. **Integration neu laden**: **Settings -- Integrations -- PilotSuite -- Menue -- Reload**

### Sensoren unavailable

**Symptom:** Sensoren zeigen `unavailable` oder `unknown`.

| Ursache | Loesung |
|---------|---------|
| Core Add-on offline | Add-on starten/neustarten |
| Coordinator-Timeout | Koordinator pollt alle 30s; bei Netzwerkproblemen kurz warten |
| Modul deaktiviert | Pruefe ob das betreffende Modul in den Options aktiviert ist |
| Fehlende Konfiguration | Z.B. Waste/Birthday-Sensoren brauchen konfigurierte Kalender/Entities |

### Webhook-Probleme

**Symptom:** Core sendet keine Echtzeit-Updates (Mood, Vorschlaege).

**Loesungen:**

1. **Webhook-URL pruefen**: Options Flow -- Settings zeigt die generierte Webhook-URL
2. **Token abgleichen**: Webhook-Token muss mit dem Token in der Core-Konfiguration uebereinstimmen
3. **Interner Zugriff**: Webhook-URL muss vom Core Add-on erreichbar sein (gleicher Host)
4. **Manueller Test**: Im Log nach `Rejected webhook: invalid token` suchen

### Events Forwarder sendet nicht

**Symptom:** Queue-Depth steigt, Events kommen nicht beim Core an.

1. `events_forwarder_enabled` muss `true` sein
2. Core Add-on muss auf Port 8909 erreichbar sein
3. `sensor.ai_home_copilot_forwarder_error_streak` pruefen
4. Entities-Allowlist pruefen: Sind die gewuenschten Entities in Zonen oder der additional_entities-Liste?

### Habituszonen-Fehler

**Symptom:** Zone kann nicht erstellt werden.

- Jede Zone braucht mindestens **1 Motion/Presence-Entity** + **1 Light-Entity**
- Zone-IDs muessen eindeutig sein
- Bulk-Edit: YAML/JSON-Syntax pruefen; Fehlermeldung zeigt Parse/Validation-Details

### Allgemeine Tipps

- **Integration neu laden**: Loest die meisten transienten Probleme
- **HA neustarten**: Bei hartnaeeckigen Problemen nach Konfigurationsaenderungen
- **HACS Update**: Sicherstellen, dass die neueste Version installiert ist
- **Core Add-on Logs**: `docker logs addon_copilot_core` fuer Backend-Fehler pruefen
- **Diagnostics**: Unter **Settings -- Integrations -- PilotSuite -- Menue -- Download diagnostics** stehen sanitisierte Debug-Informationen zur Verfuegung

---

## 11. Privacy

PilotSuite verfolgt einen **Privacy-first, Local-first** Ansatz. Alle Daten bleiben lokal.

### Keine Cloud-Abhaengigkeit

- Alle Verarbeitung findet lokal statt (HA + Core Add-on)
- Kein externer API-Zugriff
- Kein Telemetrie-Upload
- Kein Account-Zwang

### PII-Redaktion

Das Modul `privacy.py` implementiert systematische Redaktion sensibler Daten:

| Pattern | Behandlung |
|---------|-----------|
| E-Mail-Adressen | `[REDACTED_EMAIL]` |
| Telefonnummern | `[REDACTED_PHONE]` |
| Oeffentliche IP-Adressen | `[REDACTED_IP]` |
| Private IP-Adressen | Teilweise maskiert (z.B. `192.168.x.x`) |
| JWTs und Bearer Tokens | `[REDACTED_SECRET]` |
| URLs mit Token-Parametern | `[REDACTED_URL]` |
| Lange Base64/Hex-Strings | `[REDACTED_SECRET]` |

### Bounded Storage

- Alle String-Werte werden auf konfigurierbare Maximallaengen begrenzt (Standard: 500 Zeichen)
- Objekte werden mit begrenzter Rekursionstiefe (4 Ebenen) traversiert
- Listen und Dicts sind auf 200 Eintraege pro Ebene begrenzt
- Event-Buffer und Histories haben feste Groessenlimits
- Persistente Queue: konfigurierbar, Standard max. 500 Events
- Mood-History: Standard max. 100 Eintraege
- Suggestion-History: Standard max. 200 Eintraege

### Opt-in Design

Folgende Features sind standardmaessig **deaktiviert** und muessen explizit aktiviert werden:

| Feature | Config Key | Standard |
|---------|-----------|----------|
| Events Forwarder | `events_forwarder_enabled` | `false` |
| Persistent Queue | `events_forwarder_persistent_queue_enabled` | `false` |
| call_service Forwarding | `events_forwarder_forward_call_service` | `false` |
| HA Error Digest | `ha_errors_digest_enabled` | `false` |
| DevLog Push | `devlog_push_enabled` | `false` |
| ML Context | `ml_enabled` | `false` |
| Watchdog | `watchdog_enabled` | `false` |
| Multi-User Learning (MUPL) | `mupl_enabled` | `false` |
| Calendar Context | `calendar_context_enabled` | `false` |
| Waste Reminders | `waste_enabled` | `false` |
| Birthday Reminders | `birthday_enabled` | `false` |

### Domain-Projektion

Der Events Forwarder sendet nur die absolut notwendigen Attribute pro Domain (N3-Spezifikation). Beispiel:

- `light`: Nur brightness, color_temp, color_mode (keine Firmware-Infos, keine Netzwerk-Details)
- `person`: Nur source_type (keine GPS-Koordinaten, keine IP-Adressen)
- `media_player`: Nur media_type, title, source, volume (kein Album-Art, keine Account-Infos)

### MUPL Privacy

Das Multi-User Preference Learning Modul bietet zwei Privacy-Modi:

| Modus | Beschreibung |
|-------|-------------|
| `opt-in` (Standard) | Nur explizit freigegebene Benutzer werden getrackt |
| `opt-out` | Alle Benutzer werden getrackt, einzelne koennen sich abmelden |

Retention ist begrenzt (Standard: 90 Tage, konfigurierbar 1-3650 Tage).
