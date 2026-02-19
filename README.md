# PilotSuite — Styx (HACS Integration)

[![Release](https://img.shields.io/github/v/release/GreenhillEfka/ai-home-copilot-ha)](https://github.com/GreenhillEfka/ai-home-copilot-ha/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![CI](https://github.com/GreenhillEfka/ai-home-copilot-ha/actions/workflows/ci.yml/badge.svg)](https://github.com/GreenhillEfka/ai-home-copilot-ha/actions)

Home Assistant Custom Integration fuer **PilotSuite — Styx**, einen privacy-first, lokalen KI-Assistenten der die Muster deines Zuhauses lernt und intelligente Automatisierungen vorschlaegt.

Diese Integration verbindet sich mit dem [Core Add-on](https://github.com/GreenhillEfka/Home-Assistant-Copilot) (Port 8909) und stellt **94+ Sensoren**, **28 Module** und **Dashboard Cards** in Home Assistant bereit.

## Schnellstart

### Voraussetzung

Das **Core Add-on** muss installiert und gestartet sein:
[Home-Assistant-Copilot](https://github.com/GreenhillEfka/Home-Assistant-Copilot#installation)

### HACS Installation

1. [HACS](https://hacs.xyz) oeffnen
2. **Integrations** → Menue (⋮) → **Custom repositories**
3. URL eingeben: `https://github.com/GreenhillEfka/ai-home-copilot-ha` — Typ: **Integration**
4. **PilotSuite** installieren und Home Assistant **neustarten**

### Setup

1. **Settings** → **Devices & services** → **Add integration** → **PilotSuite**
2. **Zero Config** waehlen — Styx startet sofort mit Standardwerten

Alternativ: **Quick Start** (gefuehrter Wizard) oder **Manual Setup** (Host/Port/Token manuell).

## 28 Module

| Modul | Funktion |
|-------|----------|
| EventsForwarder | HA Events an Core senden (batched, PII-redacted, persistent queue) |
| HabitusMiner | Pattern-Discovery, Zone-Management, Association Rules |
| CandidatePoller | Vorschlaege vom Core abholen (5min Intervall) |
| BrainGraphSync | Brain Graph Synchronisation mit Core |
| MoodContextModule | Mood-Integration (Comfort/Joy/Frugality) |
| MediaContextModule | Media-Player Tracking (Musik, TV, Zonen) |
| MediaContextV2 | Erweiterte Media-Zonen mit automatischer Area-Erkennung |
| EnergyContextModule | Energiemonitoring (PV, Grid, Kosten) |
| WeatherContextModule | Wetter-Integration und Vorhersage |
| UniFiModule | Netzwerk-Ueberwachung (Geraete, Clients) |
| MLContextModule | ML-Kontext und Feature-Extraktion |
| UserPreferenceModule | Multi-User Preference Learning (MUPL) |
| CharacterModule | Styx-Persoenlichkeit und Kontext |
| HomeAlertsModule | Kritische Zustandsueberwachung |
| VoiceContext | Sprachsteuerungs-Kontext |
| KnowledgeGraphSync | Knowledge Graph Synchronisation |
| HouseholdModule | Familienkonfiguration und Altersgruppen |
| NeuronsModule | 14 Bewertungs-Neuronen |
| HabitusZonesV2 | Habituszonen-Verwaltung und Dashboard |
| SeedAdapterModule | Suggestion-Seed Pipeline |
| CalendarModule | Kalender-Integration |
| WasteModule | Abfuhr-Erinnerungen (TTS) |
| BirthdayModule | Geburtstags-Erinnerungen (TTS) |
| HAErrorsDigest | HA-Fehler Benachrichtigungen |
| DevlogPush | Log-Snippets an Core |
| EventsForwarderPersistent | Crash-sichere Event-Queue |
| Watchdog | Fallback-Polling |
| SafetyBackup | Konfigurations-Snapshots |

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

## Habituszonen

Habituszonen sind unabhaengig von HA Areas — sie definieren kuratierte Raeume mit Motion/Praesenz + Licht + optionalen Sensoren. CoPilot lernt zonenspezifische Muster und schlaegt passende Automatisierungen vor.

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
| [Core Add-on](https://github.com/GreenhillEfka/Home-Assistant-Copilot) | Backend, API, Brain Graph, Mood Engine |

## Lizenz

Dieses Projekt ist privat. Alle Rechte vorbehalten.
