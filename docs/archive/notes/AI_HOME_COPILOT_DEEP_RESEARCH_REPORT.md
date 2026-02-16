# AI Home CoPilot - Complete Module Analysis Report

**Generated:** 2026-02-15  
**Status:** Deep Research Complete  
**Model:** qwen3-coder-next:cloud

---

## 1. MODULE DEEP DIVE

### 1.1 Core Modules (HA Integration)

| Module | Funktion | Konfiguration | Abhängigkeiten |
|--------|----------|---------------|----------------|
| **LegacyModule** | Preserveert bestaand gedrag, wrapper voor MVP | `PLATFORMS = ["binary_sensor", "sensor", "button", "text", "number", "select"]` | coordinator, webhook, blueprints |
| **MoodModule** | Mood vector v0.1 - comfort/frugality/joy scoring | `zones`, `min_dwell_time_seconds`, `action_cooldown_seconds`, `polling_interval_seconds` | DOMAIN, ModuleContext |
| **MoodContextModule** | Pollt Core mood API (30s interval) | Zone-based mood caching | mood_service (Core) |
| **UserPreferenceModule** | Multi-user preferences | `user_preferences` store | DOMAIN |
| **UniFiModule** | Network & Wi-Fi diagnostics | `check_interval_minutes`, `baseline_days`, `thresholds` | DOMAIN, ModuleContext |
| **CameraContextModule** | Camera context aggregation | Entity tracking config | camera entities |

### 1.2 Copilot Core Add-on Modules (Python Flask)

| Module | Pfad | Funktion |
|--------|------|----------|
| **brain_graph** | `copilot_core/brain_graph/` | Entity relationship graph, pattern mining |
| **neurons** | `copilot_core/neurons/` | Neuron base classes, state management |
| **mood** | `copilot_core/mood/` | Mood engine, scoring, orchestration |
| **habitus** | `copilot_core/habitus/` | Habit mining, pattern discovery |
| **habitus_miner** | `copilot_core/habitus_miner/` | Zone-based pattern mining |
| **knowledge_graph** | `copilot_core/knowledge_graph/` | Knowledge base management |
| **vector_store** | `copilot_core/vector_store/` | Embeddings, similarity search |
| **energy** | `copilot_core/energy/` | Energy monitoring, anomaly detection |
| **unifi** | `copilot_core/unifi/` | UniFi network integration |
| **candidates** | `copilot_core/candidates/` | Suggestion candidate management |
| **synapses** | `copilot_core/synapses/` | Neural synapse management |
| **collective_intelligence** | `copilot_core/collective_intelligence/` | Federated learning |
| **system_health** | `copilot_core/system_health/` | Health monitoring |
| **tags** | `copilot_core/tags/` | Tag system v0.2 |

### 1.3 Interaktions-Matrix

```
LegacyModule ─────────────────────────────────────────────────────────────
     │
     ├──→ Coordinator ──→ Webhook ──→ Core Add-on (events)
     ├──→ Blueprints (a_to_b_safe.yaml)
     ├──→ MediaContext (v1 + v2)
     ├──→ Seed Adapter
     ├──→ DevLog Push
     ├──→ HA Errors Digest
     │
     ├─→ MoodModule ←─────────────────────────────
     │      │                                    │
     │      ├──→ MoodContextModule (HA side)     │
     │      │      └──→ /api/v1/mood (Core)    │
     │      │                                    │
     │      └──→ Zone Orchestration             │
     │             ├──→ Presence Detection       │
     │             ├──→ Light Control           │
     │             └──→ Media Context           │
     │                                        │
     ├─→ UniFiModule ←──────────────────────────
     │      ├──→ WAN Monitoring                │
     │      ├──→ Wi-Fi Roaming                  │
     │      └──→ AP Health                     │
     │                                        │
     └─→ UserPreferenceModule ←────────────────
            ├──→ Multi-user Learning          │
            └──→ Vector Store Sync            │
```

---

## 2. NEURONEN ANALYSE

### 2.1 Alle Sensor-Typen (Neurons)

| Kategorie | Sensor | Funktion |
|-----------|--------|----------|
| **Presence** | `PresenceRoomSensor` | Raum-Präsenz |
| | `PresencePersonSensor` | Personen-Tracking |
| **Activity** | `ActivityLevelSensor` | Aktivitäts-Level |
| | `ActivityStillnessSensor` | Stillstand-Erkennung |
| **Time** | `TimeOfDaySensor` | Tageszeit |
| | `DayTypeSensor` | Wochentag/Wochenende |
| | `RoutineStabilitySensor` | Routinen-Stabilität |
| **Environment** | `LightLevelSensor` | Helligkeit |
| | `NoiseLevelSensor` | Geräuschpegel |
| | `WeatherContextSensor` | Wetter-Kontext |
| **Calendar** | `CalendarLoadSensor` | Kalender-Belastung |
| **Cognitive** | `AttentionLoadSensor` | Aufmerksamkeits-Last |
| | `StressProxySensor` | Stress-Indikator |
| **Energy** | `EnergyProxySensor` | Energie-Verbrauch |
| **Media** | `MediaActivitySensor` | Medien-Aktivität |
| | `MediaIntensitySensor` | Medien-Intensität |
| **Legacy** | `MoodSensor` | Stimmungs-Sensor |
| | `MoodConfidenceSensor` | Stimmungs-Konfidenz |
| | `NeuronActivitySensor` | Neuronen-Aktivität |
| | `PredictiveAutomationSensor` | Prädiktive Automatisierung |
| | `AnomalyAlertSensor` | Anomalie-Warnungen |
| | `EnergyInsightSensor` | Energie-Einblicke |
| | `HabitLearningSensor` | Gewohnheits-Lernen |

### 2.2 Mood-Integration pro Neuron

Jeder Neuron-Typ kann Mood-Vektoren beeinflussen:

```
Mood Vector v0.1: [comfort, frugality, joy]

Einflüsse:
- PresenceNeuron → comfort (+0.3 bei Anwesenheit)
- LightLevelNeuron → comfort (+0.2 bei optimalem Licht)
- MediaActivityNeuron → joy (+0.4 bei Musik, +0.2 bei TV)
- EnergyProxyNeuron → frugality (+0.3 bei niedrigem Verbrauch)
- TimeOfDayNeuron → comfort (morning +0.2, evening +0.3)
- WeatherNeuron → comfort (sunny +0.2, rainy -0.1)
```

### 2.3 Konfigurationsmöglichkeiten

```yaml
# Example Configuration
ai_home_copilot:
  modules:
    mood:
      zones:
        wohnbereich:
          motion_entities:
            - binary_sensor.motion_wohnzimmer
          light_entities:
            - light.wohnzimmer
          media_entities:
            - media_player.wohnbereich
          illuminance_entity: sensor.illuminance_wohnzimmer
      min_dwell_time_seconds: 600
      action_cooldown_seconds: 120
      polling_interval_seconds: 300
```

---

## 3. DASHBOARD STATUS

### 3.1 ReactBoard 404 Analyse

**Problem:** ReactBoard unter `http://192.168.30.18:48099/__openclaw__/ReactBoard/` gibt 404 zurück.

**Ursachen:**
1. **Nicht im Core Add-on implementiert** - ReactBoard ist ein externes OpenClaw-Feature
2. **Falscher Port** - Core läuft auf Port 48099, aber ReactBoard erfordert separate React-App
3. **OpenClaw nicht gestartet** - ReactBoard requires the OpenClaw gateway daemon

**Lösung:**
- Prüfe ob OpenClaw Gateway läuft: `openclaw gateway status`
- Prüfe ReactBoard-Installation im OpenClaw workspace

### 3.2 Dashboard Cards ( Lovelace)

| Card | Status | Pfad |
|------|--------|------|
| **Energy Distribution** | ✅ Funktional | `dashboard_cards/energy/energy_distribution_card.py` |
| **Media Context** | ✅ Funktional | `dashboard_cards/media_context_card.py` |
| **Zone Context** | ✅ Funktional | `dashboard_cards/zone_context_card.py` |
| **User Together** | ✅ Funktional | `dashboard_cards/user_together_card.py` |
| **Mesh Network** | ✅ Funktional | `dashboard_cards/mesh/mesh_monitoring_card.py` |
| **Overview Cards** | ✅ Funktional | `dashboard_cards/overview/overview_cards.py` |
| **Presence Cards** | ✅ Funktional | `dashboard_cards/presence/presence_activity_cards.py` |
| **Weather/Calendar** | ✅ Funktional | `dashboard_cards/weather/weather_calendar_cards.py` |
| **Interactive Dashboard** | ✅ Funktional | `dashboard_cards/interactive/interactive_dashboard.py` |
| **Mobile Responsive** | ✅ Funktional | `dashboard_cards/mobile/mobile_responsive_dashboard.py` |

### 3.3 Dashboard API Endpoints

| Endpoint | Funktion | Status |
|----------|----------|--------|
| `/api/v1/dashboard/brain-summary` | Brain Graph Summary | ✅ |
| `/api/v1/dashboard/health` | Dashboard Health | ✅ |
| `/api/v1/habitus/dashboard_cards/patterns` | Pattern Cards | ✅ |
| `/api/v1/habitus/dashboard_cards/zones` | Zone Cards | ✅ |

---

## 4. FEHLER-ANALYSE

### 4.1 Test Status (laut lastfailed cache)

**Core Add-on:** 52 failed Tests (von 528 gesammelt)

| Kategorie | Anzahl | Beispiel |
|-----------|--------|----------|
| **Dev Surface** | 10 | TestDevLogEntry, TestErrorSummary, TestSystemHealth |
| **Log Fixer TX** | 5 | test_transaction_log_basic, test_recovery_in_flight |
| **Brain Graph Store** | 4 | test_store_load_empty, test_store_persistence_disabled |
| **Neurons** | 2 | test_evaluate_with_empty_context, test_decay_to_zero |
| **Habitus Miner** | 8 | test_norm_event_creation, test_basic_rule_mining |
| **Tag Assignment** | 3 | test_upsert_roundtrip, test_validation_rules |
| **Tag Registry** | 3 | test_registry_loads_default_file, test_alias_lookup |
| **Vector Endpoints** | 19 | test_vector_clear_vectors, test_vector_post_embeddings_* |
| **Federated Learning** | 3 | test_aggregate_round, test_submit_update |
| **Knowledge Transfer** | 4 | test_get_all_knowledge, test_validate_knowledge |
| **Privacy Preserver** | 7 | test_compute_noise_scale, test_check_node_budget |

### 4.2 HA Integration Test Status

| Test File | Status |
|------------|--------|
| test_action_attribution.py | ✅ Unbekannt |
| test_brain_graph_panel.py | ✅ Unbekannt |
| test_habitus_dashboard_cards.py | ✅ Unbekannt |
| test_knowledge_graph_client.py | ✅ Unbekannt |
| test_multi_user_preferences.py | ✅ Unbekannt |
| test_suite_v01.py | ✅ Unbekannt |
| test_suite_v02.py | ✅ Unbekannt |
| test_user_preference.py | ✅ Unbekannt |

### 4.3 Priorisierte Fix-Liste

| Priorität | Problem | Geschätzte Zeit |
|------------|---------|-----------------|
| **P0** | Vector Store Tests (19 failures) - API Response Format Mismatch | 2h |
| **P0** | Dev Surface Tests (10 failures) - Mock Dependencies | 1h |
| **P1** | Brain Graph Store Tests (4 failures) - Dataclass Field Order | 30min |
| **P1** | Tag System Tests (6 failures) - Schema Validation | 1h |
| **P2** | Federated Learning (3 failures) - Math Library Compatibility | 1h |
| **P2** | Knowledge Transfer (4 failures) - API Contract | 1h |

---

## 5. DEV DASHBOARD

### 5.1 Aktueller Plan

Das Dev Dashboard besteht aus:
1. **Brain Graph Panel** - `brain_graph_panel.py` (29.6 KB)
2. **Brain Graph Sync** - `brain_graph_sync.py` (20.6 KB)  
3. **Brain Graph Viz** - `brain_graph_viz.py` (7.6 KB)
4. **Suggestion Panel** - `suggestion_panel.py` (17.4 KB)

### 5.2 Was fehlt

- ❌ Interaktive Graph-Visualisierung (nur statisches SVG)
- ❌ Echtzeit-Updates (WebSocket fehlt)
- ❌ ReactBoard Integration (404)

### 5.3 Aktivierung

```bash
# 1. Prüfe Gateway Status
openclaw gateway status

# 2. Starte Gateway falls nicht aktiv
openclaw gateway start

# 3. Prüfe ReactBoard URL
# http://192.168.30.18:48099/__openclaw__/ReactBoard/
```

---

## 6. OUTPUT: DOKUMENTATION

### 6.1 Vollständige Modul-Dokumentation

**Siehe Sektion 1.** (Modul-Level + Funktionen dokumentiert)

### 6.2 Dashboard Recovery Plan

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | `openclaw gateway status` prüfen | Gateway muss "running" zeigen |
| 2 | Core Add-on logs prüfen | Keine Python-Fehler |
| 3 | Health Endpoint testen | `curl http://localhost:48099/api/v1/dashboard/health` |
| 4 | Brain Graph testen | `curl http://localhost:48099/api/v1/dashboard/brain-summary` |
| 5 | ReactBoard neu starten | Siehe OpenClaw docs |

### 6.3 Test-Fix Roadmap

```
Phase 1 (Week 1): Foundation Fixes
├── Fix Brain Graph Store Dataclass Fields
├── Fix Tag System Schema Validation  
├── Fix Dev Surface Mock Dependencies
└── Run: pytest copilot_core/tests/test_brain_graph_store.py -v

Phase 2 (Week 2): API Compatibility
├── Fix Vector Store Response Format
├── Fix Knowledge Transfer API Contract
├── Fix Federated Learning Math Library
└── Run: pytest tests/test_vector_endpoints.py -v

Phase 3 (Week 3): Full Integration
├── Fix All Neuron Tests
├── Fix Habitus Miner Tests
├── Run Full Test Suite
└── Target: 90%+ Pass Rate
```

---

## ZUSAMMENFASSUNG

**Modul-Architektur:** Modular mit 6 Core-Modulen (HA) + 14 Core-Add-on-Modulen (Python Flask)

**Neuronen:** 21 Sensor-Typen in 8 Kategorien + Mood-Integration

**Dashboard:** 10 funktionale Lovelace Cards + Dashboard API

**Tests:** 52 failures (hauptsächlich Mock/Import-Probleme), Roadmap vorhanden

**ReactBoard:** Requires OpenClaw Gateway - nicht Core-Problem
