# AI Home CoPilot — HACS Integration

[![Release](https://img.shields.io/github/v/release/GreenhillEfka/ai-home-copilot-ha)](https://github.com/GreenhillEfka/ai-home-copilot-ha/releases)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)

Home Assistant Custom Integration für den **AI Home CoPilot** — privacy-first, lokaler KI-Assistent der die Muster deines Zuhauses lernt.

Diese Integration verbindet sich mit dem [Core Add-on](https://github.com/GreenhillEfka/Home-Assistant-Copilot) (Port 8099) und stellt **80+ Sensoren**, **15+ Dashboard Cards** und **22 Core-Module** in Home Assistant bereit.

## Installation

### Voraussetzung

Das **Core Add-on** muss installiert und gestartet sein:
[Home-Assistant-Copilot](https://github.com/GreenhillEfka/Home-Assistant-Copilot#installation)

### HACS Integration installieren

1. [HACS](https://hacs.xyz) installieren (falls noch nicht vorhanden)
2. HACS → **Integrations** → Menü (⋮) → **Custom repositories**
3. Repository-URL hinzufügen:
   ```
   https://github.com/GreenhillEfka/ai-home-copilot-ha
   ```
   Typ: **Integration**
4. **AI Home CoPilot** über HACS installieren
5. Home Assistant **neustarten**

### Setup

1. **Settings** → **Devices & services** → **Add integration** → **AI Home CoPilot**
2. Konfiguration ausfüllen:

| Feld | Standard | Beschreibung |
|------|----------|-------------|
| Host | `homeassistant.local` | HA Host LAN-IP/Hostname |
| Port | `8099` | Core Add-on Port |
| API Token | _(optional)_ | Token-Authentifizierung |
| Test Light | _(optional)_ | Entity für Demo-Toggle |

Weitere Optionen (über Options-Flow konfigurierbar):
- **Events Forwarder** — Batch-Größe, Flush-Intervall, Persistent Queue, Idempotency
- **Suggestion Seed** — Erlaubte Domains, Max Offers/Stunde, Seed-Entities
- **Media Player** — Musik- und TV-Player zuordnen
- **Habitus Zones** — Zonen-Konfiguration für Pattern-Discovery
- **Watchdog** — Überwachungsintervall
- **User Preferences** — Multi-User Preference Learning (MUPL)

### Update / Rollback

HACS erstellt ein `update.*`-Entity für das Repository.

- **Update:** HACS UI oder `update.install` Service
- **Rollback:** `update.install` mit `version` auf einen Git-Tag setzen

## Features

### 22 Core-Module

| Modul | Funktion |
|-------|----------|
| EventsForwarder | HA Events → Core (batched, rate-limited, PII-redacted) |
| HabitusModule | Pattern-Discovery und Zone-Management |
| CandidatePollerModule | Vorschläge vom Core abholen (5min Intervall) |
| BrainSyncModule | Brain Graph Synchronisation |
| MoodContextModule | Mood-Integration und Kontext |
| MediaModule | Media-Player Tracking |
| EnergyModule | Energiemonitoring |
| WeatherModule | Wetter-Integration |
| UniFiModule | Netzwerk-Überwachung |
| MLContextModule | ML-Kontext und Features |
| MUPLModule | Multi-User Preference Learning |
| CharacterModule | CoPilot-Persönlichkeit |
| ... | und weitere |

### 80+ Sensoren

| Sensor-Gruppe | Beispiele |
|---------------|-----------|
| Mood | `sensor.copilot_mood`, Mood-Dimensionen |
| Presence | Anwesenheitserkennung |
| Activity | Aktivitätserkennung |
| Energy / Energy Insights | PV, Grid, Kosten |
| Neurons (14+) | Time, Calendar, Cognitive, Context |
| Anomaly Alert | Anomalie-Erkennung |
| Predictive Automation | Prädiktive Vorschläge |
| Environment | Temperatur, Feuchtigkeit |
| Calendar | Kalender-Integration |
| Media | Media-Player Status |
| Habit Learning v2 | Gewohnheitslernen |
| Voice Context | Sprachsteuerung |

### 15+ Dashboard Cards

Brain Graph, Mood Card, Neurons Card, Habitus Card, und mehr — als Lovelace Custom Cards.

### Blueprint

Eine sichere A→B Automation-Blueprint wird mitgeliefert:
`/config/blueprints/automation/ai_home_copilot/a_to_b_safe.yaml`

Erstellt **keine** Automatisierung automatisch — nur auf Freigabe.

## Grundprinzipien

- **Local-first** — Alles lokal, keine Cloud
- **Privacy-first** — PII-Redaktion, bounded Storage, opt-in
- **Governance-first** — Vorschläge vor Aktionen, Human-in-the-Loop
- **Safe Defaults** — Sicherheitsrelevante Aktionen immer Manual Mode

## Dokumentation

- **[VISION.md](https://github.com/GreenhillEfka/Home-Assistant-Copilot/blob/main/VISION.md)** — Single Source of Truth
- **[USER_MANUAL.md](docs/USER_MANUAL.md)** — Benutzerhandbuch (deutsch)
- **[CHANGELOG.md](CHANGELOG.md)** — Release-Historie

## Lizenz

Dieses Projekt ist privat. Alle Rechte vorbehalten.
