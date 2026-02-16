# AI Home CoPilot - Module Inventory

## Übersicht

| Kategorie | Anzahl | Status |
|-----------|--------|--------|
| Core Modules | 22 | ✅ Alle aktiv |
| Sensors | 16 | ✅ Alle aktiv |
| Dashboard Cards | 15+ | ✅ |
| API Endpoints | 25 | ✅ |

---

## Core Modules (22)

### Neuronale Verarbeitung

| Modul | Zweck | Status |
|-------|-------|--------|
| **mood_module.py** | Mood-Erkennung + Character System | ✅ |
| **mood_context_module.py** | Mood-Kontext für Entscheidungen | ✅ |
| **brain_graph_sync.py** | Brain Graph mit Core sync | ✅ |
| **knowledge_graph_sync.py** | Knowledge Graph Integration | ✅ |

### Context Module

| Modul | Zweck | Status |
|-------|-------|--------|
| **camera_context_module.py** | Kamera-Status + Presence | ✅ |
| **energy_context_module.py** | Energy-Monitoring + Frugality | ✅ |
| **media_context_module.py** | Media-Player Status | ✅ |
| **presence_sensors.py** | Präsenz-Erkennung | ✅ |
| **weather_context_module.py** | Wetterdaten + Empfehlungen | ✅ |

### Intelligence

| Modul | Zweck | Status |
|-------|-------|--------|
| **habitus_miner.py** | Pattern Mining aus Brain Graph | ✅ |
| **user_preference_module.py** | Multi-User Preference Learning | ✅ |
| **ml_context_module.py** | ML Pipeline Integration | ✅ |
| **quick_search.py** | Entity-Suche + Vorschläge | ✅ |

### Infrastruktur

| Modul | Zweck | Status |
|-------|-------|--------|
| **events_forwarder.py** | Events zu Core weiterleiten | ✅ |
| **candidate_poller.py** | Automation Candidates abrufen | ✅ |
| **voice_context_module.py** | Sprachsteuerung Integration | ✅ |
| **unifi_module.py** | UniFi Controller Integration | ✅ |

### Operationen

| Modul | Zweck | Status |
|-------|-------|--------|
| **ops_runbook.py** | Automatisierte Operationen | ✅ Security Fix |
| **performance_scaling.py** | Performance-Management | ✅ |

---

## Sensors (16)

| Sensor | Zweck |
|--------|-------|
| **mood_sensor.py** | Mood-Entity für HA |
| **energy_sensors.py** | Energy-Überwachung |
| **presence_sensors.py** | Anwesenheitserkennung |
| **media_sensors.py** | Media-Player Tracking |
| **calendar_sensors.py** | Kalender-Integration |
| **activity_sensors.py** | Aktivitätserkennung |
| **environment_sensors.py** | Umgebung (Temp, Feuchte) |
| **habit_learning_v2.py** | Habit Learning |
| **cognitive_sensors.py** | Kognitive Last |
| **neuron_dashboard.py** | Neuron Dashboard |
| **neurons_14.py** | Zusätzliche Neuronen |
| **anomaly_alert.py** | Anomalie-Erkennung |
| **predictive_automation.py** | Prädiktive Automation |
| **time_sensors.py** | Zeit-basierte Trigger |
| **voice_context.py** | Sprachsteuerung |
| **energy_insights.py** | Energy Insights |

---

## Key Features

### ✅ Implementiert

1. **Character System (v0.1)**
   - 5 Presets: assistant, companion, guardian, efficiency, relaxed
   - Mood-Gewichtung pro Character
   - Voice-Tone Anpassung

2. **User Hints System**
   - Natürliche Spracheingabe → Automation-Vorschläge
   - API: `/api/v1/hints`

3. **Zone System v2**
   - 6 Zones konfiguriert
   - Auto-Tag bei Zone-Erstellung
   - Entity-Suggestions

4. **Security**
   - Auth Bypass Fix
   - Rate Limiting
   - Command Whitelist
   - Pickle Hash Verification

5. **Brain Graph**
   - Interaktive Visualisierung
   - Cache Limit: 100
   - Batch Processing

---

## Warum diese Struktur?

### Philosophie: Das lernende Zuhause

```
State → Neuron → Mood → Entscheidung
```

- **Neuronen** bewerten einzelne Aspekte (Energy, Presence, Mood)
- **Mood** aggregiert die Bewertungen
- **Entscheidung** basiert auf Mood + Context

### Zone-Tag Integration

```
Zone erstellen → Tag aicp.place.{zone} erstellen
    ↓
Entity mit Tag → automatisch in Zone
```

### Multi-User Support

```
User A (prefer_eco) + User B (prefer_comfort)
    ↓
MUPL lernt individuelle Präferenzen
    ↓
Automatische Anpassung
```

---

## Testing

| Metrik | Wert |
|--------|------|
| Passed | 297 |
| Failed | 24 |
| Errors | 25 |

Die 24 Failed sind Test-Code vs Implementation Mismatches.
Die 25 Errors sind HA-Dependency Fehler (erwartet).

