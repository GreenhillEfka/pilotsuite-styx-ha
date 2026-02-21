# PilotSuite — Styx (HACS Integration)

[![Release](https://img.shields.io/github/v/release/GreenhillEfka/pilotsuite-styx-ha)](https://github.com/GreenhillEfka/pilotsuite-styx-ha/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![CI](https://github.com/GreenhillEfka/pilotsuite-styx-ha/actions/workflows/ci.yml/badge.svg)](https://github.com/GreenhillEfka/pilotsuite-styx-ha/actions)

Home Assistant Custom Integration fuer **PilotSuite — Styx**, einen privacy-first, lokalen KI-Assistenten der die Muster deines Zuhauses lernt und intelligente Automatisierungen vorschlaegt.

Diese Integration verbindet sich mit dem [Core Add-on](https://github.com/GreenhillEfka/pilotsuite-styx-core) (Port 8909) und stellt **94+ Sensoren**, **30 Module** und **Dashboard Cards** in Home Assistant bereit.

## Schnellstart

### Voraussetzung

Das **Core Add-on** muss installiert und gestartet sein:
[pilotsuite-styx-core](https://github.com/GreenhillEfka/pilotsuite-styx-core#installation)

### HACS Installation

1. [HACS](https://hacs.xyz) oeffnen
2. **Integrations** → Menue (⋮) → **Custom repositories**
3. URL eingeben: `https://github.com/GreenhillEfka/pilotsuite-styx-ha` — Typ: **Integration**
4. **PilotSuite** installieren und Home Assistant **neustarten**

### Setup

1. **Settings** → **Devices & services** → **Add integration** → **PilotSuite**
2. **Zero Config** waehlen — Styx startet sofort mit Standardwerten

Alternativ: **Quick Start** (gefuehrter Wizard) oder **Manual Setup** (Host/Port/Token manuell).

## 30 Module

| Modul | Funktion |
|-------|----------|
| EventsForwarder | HA Events an Core senden (batched, PII-redacted, persistent queue) |
| HabitusMiner | Pattern-Discovery, Zone-Management, Association Rules |
| CandidatePoller | Vorschlaege vom Core abholen (5min Intervall) |
| BrainGraphSync | Brain Graph Synchronisation mit Core |
| MoodModule | Mood-Sensoren (Comfort/Joy/Frugality) |
| MoodContextModule | Mood-Integration und Kontext |
| MediaContextModule | Media-Player Tracking (Musik, TV, Zonen) |
| EnergyContextModule | Energiemonitoring (PV, Grid, Kosten) |
| WeatherContextModule | Wetter-Integration und Vorhersage |
| UniFiModule | Netzwerk-Ueberwachung (Geraete, Clients) |
| MLContextModule | ML-Kontext und Feature-Extraktion |
| UserPreferenceModule | Multi-User Preference Learning (MUPL) |
| CharacterModule | Styx-Persoenlichkeit und Kontext |
| HomeAlertsModule | Kritische Zustandsueberwachung |
| VoiceContext | Sprachsteuerungs-Kontext |
| KnowledgeGraphSync | Knowledge Graph Synchronisation |
| CameraContextModule | Frigate/Kamera-Integration mit Privacy |
| CalendarModule | Kalender-Integration und Kontext |
| WasteReminderModule | Abfuhr-Erinnerungen (TTS) |
| BirthdayReminderModule | Geburtstags-Erinnerungen (TTS) |
| EntityTagsModule | Entity-Tag-System fuer Kategorisierung |
| PersonTrackingModule | Personen-Tracking und Praesenz |
| FrigateBridgeModule | Frigate NVR Bridge |
| SceneModule | Szenen-Verwaltung und Empfehlungen |
| HomeKitBridgeModule | HomeKit-Bridge Integration |
| QuickSearchModule | Schnellsuche ueber Entitaeten |
| DevSurfaceModule | Debug- und Diagnose-Buttons |
| PerformanceScalingModule | Performance-Monitoring |
| OpsRunbookModule | Preflight-Checks und Smoke-Tests |
| LegacyModule | Rueckwaertskompatibilitaet |

## 94+ Sensoren

| Gruppe | Beispiele |
|--------|-----------|
| Mood | Comfort, Joy, Frugality, Zone-Moods |
| Neurons (14) | Time, Calendar, Cognitive, Presence, Energy, Weather, Context |
| Habitus | Zone-Status, Patterns, Mining-Stats |
| Energy | PV-Produktion, Grid, Kosten, Insights |
| Media | Player-Status, Now Playing, Zonen |
| Brain Graph | Nodes, Edges, Patterns |
| Anomaly | Alert-Status, Predictions |
| Calendar | Events, Focus/Social Weight |
| Waste/Birthday | Naechste Abholung, Geburtstage |
| System | Health Score, API Status, Version |

## Styx als Chat-Assistent einrichten

PilotSuite stellt eine OpenAI-kompatible API bereit (`/v1/chat/completions`). So wird Styx zum Gespraechspartner:

### Option 1: Extended OpenAI Conversation (empfohlen)

1. [Extended OpenAI Conversation](https://github.com/jekalmin/extended_openai_conversation) via HACS installieren
2. **Settings** → **Devices & services** → **Add integration** → **Extended OpenAI Conversation**
3. Konfigurieren:
   - **API Key**: Auth-Token aus dem Core Add-on
   - **Base URL**: `http://homeassistant.local:8909/v1`
   - **Model**: `qwen3:4b`
4. **Settings** → **Voice Assistants** → Styx als Conversation Agent waehlen

Styx antwortet mit **26 Tools** (Geraete steuern, Automations erstellen, Einkaufsliste, Kalender, Web-Suche, Warnmeldungen, Szenen, Musiksteuerung u.v.m.) und nutzt RAG-basiertes Langzeitgedaechtnis.

### Option 2: Telegram Bot

Im Core Add-on unter **Configuration** → `telegram.enabled: true` aktivieren. Styx fuehrt Tools serverseitig aus — kein zusaetzliches HA-Setup noetig.

## Brain Graph Visualisierung

Das Core Add-on bietet ein interaktives Web-Dashboard (Dark Theme) mit D3.js Brain Graph, erreichbar ueber den Ingress-Panel-Link im Add-on:

```
 Nodes (farblich nach Domain)
 ============================

     [light.*]  o----------o  [binary_sensor.*]
       gelb     |          |     blau
                |          |
     [person.*] o----------o  [automation.*]
       gruen               |     orange
                           |
     [sensor.*] o----------o  [climate.*]
       cyan                      rot

 Edges = Beziehungen (temporal, causal, spatial)
```

Dazu: Mood-Gauges (Comfort/Joy/Frugality), Habitus-Patterns, Chat-Interface und Modul-Health-Status in Echtzeit.

## Habituszonen

Habituszonen sind unabhaengig von HA Areas — sie definieren kuratierte Raeume mit Motion/Praesenz + Licht + optionalen Sensoren. PilotSuite lernt zonenspezifische Muster und schlaegt passende Automatisierungen vor.

Verwaltung ueber **Settings → Integrations → PilotSuite → Configure → Habitus zones**.

## Grundprinzipien

- **Local-first** — Alles lokal, keine Cloud
- **Privacy-first** — PII-Redaktion, bounded Storage, opt-in
- **Governance-first** — Vorschlaege vor Aktionen, Human-in-the-Loop
- **Safe Defaults** — Sicherheitsrelevante Aktionen immer Manual Mode

## Dokumentation

| Dokument | Inhalt |
|----------|--------|
| [HANDBOOK](docs/HANDBOOK.md) | Setup, Module, Sensoren, Zonen, Troubleshooting |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | Systemdesign, Datenfluss, Entity-Struktur |
| [DEVELOPER_GUIDE](docs/DEVELOPER_GUIDE.md) | CI, Tests, Release-Prozess, Beitragen |
| [CHANGELOG](CHANGELOG.md) | Release-Historie |
| [Core Add-on](https://github.com/GreenhillEfka/pilotsuite-styx-core) | Backend, API, Brain Graph, Mood Engine |

## Lizenz

Dieses Projekt ist privat. Alle Rechte vorbehalten.
