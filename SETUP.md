# PilotSuite Styx – Vollständige Einrichtungsanleitung

## Inhalt
1. [Voraussetzungen](#voraussetzungen)
2. [Installation Core Add-on](#installation-core-add-on)
3. [Installation HA Integration](#installation-ha-integration)
4. [Zero-Config Quickstart](#zero-config-quickstart)
5. [Erweiterte Konfiguration](#erweiterte-konfiguration)
6. [Module aktivieren/deaktivieren](#module-aktivierendeaktivieren)
7. [Dashboard Einrichtung](#dashboard-einrichtung)
8. [Troubleshooting](#troubleshooting)

---

## Voraussetzungen

| Komponente | Anforderung |
|-----------|-------------|
| Home Assistant | ≥ 2024.1.0 |
| Hardware | ARM64/AMD64 (Same-Host bevorzugt für lokale LLM) |
| Ollama (optional) | ≥ 0.1.20 für lokale LLM |
| Speicher | ≥ 4GB RAM für lokale Modelle |

---

## Installation Core Add-on

### Option A: HACS (Empfohlen)

1. HACS öffnen → **Add-ons** → **...** → **Repositories hinzufügen**
2. URL: `https://github.com/GreenhillEfka/pilotsuite-styx-core`
3. **PilotSuite Core** installieren

### Option B: Manuell

1. Repository klonen: `git clone https://github.com/GreenhillEfka/pilotsuite-styx-core`
2. Als lokales Add-on hinzufügen (HA → Add-ons → Lokales Add-on)

### Erster Start

1. **PilotSuite Core** starten
2. Auf **Ingress** klicken → Dashboard öffnet sich
3. **Onboarding** durchlaufen:
   - Ollama URL: `http://host.docker.internal:11434` (falls Host Ollama)
   - Modell: `qwen3:0.6b` (schnell) oder `qwen3:4b` (besser)
   - Auth Token: Notieren für HA-Setup

---

## Installation HA Integration

### Schritt 1: HACS Custom Repository

1. **HACS** öffnen → **Integrations** → **...** → **Custom repositories**
2. URL: `https://github.com/GreenhillEfka/pilotsuite-styx-ha`
3. Typ: **Integration**
4. **PilotSuite** installieren

### Schritt 2: Integration hinzufügen

1. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. **PilotSuite** suchen und auswählen

---

## Zero-Config Quickstart

### Automatische Erkennung

Der **Zero-Config** Modus (empfohlen):
- Erkennt Core Add-on automatisch
- Verwendet Standard-Port `8909`
- Startet mit allen Modulen
- Scannt nach Medien-Playern (Sonos, Apple TV, Smart TV)
- Schlägt Habitus Zones basierend auf Entity-Namen vor

**So funktioniert's:**
1. **Zero Config** im Setup-Wizard wählen
2. Styx startet automatisch
3. Bei erstem Start: Media-Entity-Scan läuft
4. Dashboard wird automatisch generiert

### Was Zero-Config enthält

| Feature | Standard |
|---------|----------|
| Core Endpoint | Auto-Discovery (localhost:8909) |
| Auth Token | Aus Core gelesen |
| Ollama | Lokal `qwen3:0.6b` |
| Cloud Fallback | Ollama Cloud (https://ollama.com/v1) |
| Module | Alle 31 Module aktiv |
| Dashboard | Auto-generiert |
| Media Scan | Automatisch (Sonos/Apple TV/SmartTV) |

---

## Erweiterte Konfiguration

### Quick Start Wizard

Für erfahrene Benutzer:
1. **Quick Start** wählen
2. Host/Port anpassen (falls nicht Standard)
3. Entity Profile wählen:
   - **Basic**: Nur Kernfunktionen
   - **Standard**: Alle Sensoren
   - **Full**: Inkl. ML/Prediction

### Manueller Setup

1. **Manual Setup** wählen
2. Daten eingeben:
   - Host: z.B. `192.168.1.100`
   - Port: Standard `8909`
   - Token: Aus Core-Onboarding

### Optionen nachträglich ändern

**Einstellungen** → **Geräte & Dienste** → **PilotSuite** → **Konfigurieren**

Exakte Schritt-für-Schritt-Anleitung in HA anzeigen:
- Service: `ai_home_copilot.show_installation_guide`

| Option | Beschreibung |
|--------|-------------|
| Host / Port | Core Add-on Adresse |
| Token | Authentifizierung |
| Entity Profile | Funktionsumfang |
| Module | Individuell ein/aus |
| Test Light | Entity für Nachtest |

---

## Module aktivieren/deaktivieren

### Im Options Flow

1. PilotSuite → **Konfigurieren**
2. Tab **Module**
3. Gewünschte Module ein-/ausschalten

### Verfügbare Module

| Kategorie | Module |
|-----------|--------|
| **Plumbing** | Legacy, EventsForwarder, CandidatePoller, HistoryBackfill |
| **Intelligence** | HabitusMiner, BrainGraphSync, Mood, MLContext, KnowledgeGraph |
| **Kontext** | Energy, Weather, Media, Network, Camera |
| **Governance** | Character, QuickSearch, Voice, OpsRunbook |
| **Home Ops** | HomeAlerts, WasteReminder, PersonTracking, Scene, Calendar |

---

## Dashboard Einrichtung

### Automatisch (Standard)

Beim ersten Start generiert Styx:
- `/config/pilotsuite-styx/pilotsuite_dashboard_latest.yaml`
- `/config/pilotsuite-styx/habitus_zones_dashboard_latest.yaml`

Legacy-Kompatibilitaet:
- Spiegelung weiterhin unter `/config/ai_home_copilot/...`

Lovelace-Wiring wird automatisch hinzugefügt (Notification bei Erfolg).

### Manuell

Falls eigene Lovelace-Konfiguration:

```yaml
lovelace:
  dashboards:
    copilot-pilotsuite:
      mode: yaml
      title: "PilotSuite - Styx"
      icon: mdi:robot-outline
      show_in_sidebar: true
      filename: "pilotsuite-styx/pilotsuite_dashboard_latest.yaml"
    copilot-habitus-zones:
      mode: yaml
      title: "PilotSuite - Habitus Zones"
      icon: mdi:layers-outline
      show_in_sidebar: true
      filename: "pilotsuite-styx/habitus_zones_dashboard_latest.yaml"
```

---

## Ollama Konfiguration

### Lokale Ollama

1. Ollama auf Host installieren: `curl -fsSL https://ollama.com/install.sh | sh`
2. Modell laden: `ollama pull qwen3:0.6b`
3. Port prüfen: Default `11434`

### Ollama Cloud (Automatisch)

Styx verwendet bei Bedarf automatisch:
- **URL**: `https://ollama.com/v1`
- **Modell**: `gpt-oss:20b` (Fallback)

**Aktivierung:**
1. Core Add-on → **Einstellungen**
2. **Cloud API** aktivieren
3. API Key eintragen

### Modell-Empfehlungen

| Modell | Größe | Speed | Quality | Use Case |
|--------|-------|-------|---------|----------|
| qwen3:0.6b | ~400MB | ⚡⚡⚡ | ⭐⭐ | Standard, schnelle Antworten |
| qwen3:4b | ~2.5GB | ⚡⚡ | ⭐⭐⭐ | Besseres Reasoning |
| llama3.2:3b | ~2GB | ⚡⚡ | ⭐⭐⭐ | Alternative |
| mistral:7b | ~4GB | ⚡ | ⭐⭐⭐⭐ | Beste Qualität |

---

## Entity Auto-Discovery

### Was wird erkannt

| Gerätetyp | Erkennung | Zone-Inferenz |
|-----------|-----------|---------------|
| Sonos | Plattform | Aus Entity-Namen |
| Apple TV | Plattform | Aus Entity-Namen |
| Smart TV | Plattform | Aus Entity-Namen |
| Lichter | device_class | Aus Area/Name |
| Sensoren | device_class | Aus Area/Name |

### Zone-Inferenz

Styx erkennt Zonen aus:
- Entity-Namen (`Wohnzimmer TV` → `living_room`)
- HA Areas (falls konfiguriert)
- Automatische Vorschläge im Wizard

---

## Self-Heal Funktionen

### Automatisch

Styx heilt sich selbst bei:
- Ollama nicht verfügbar → Cloud-Fallback
- Modul-Ladefehler → Skip + Log
- Entity nicht verfügbar → Fallback-Werte

### Manuell

**API Endpoint**: `POST /api/v1/agent/self-heal`

```bash
curl -X POST http://localhost:8909/api/v1/agent/self-heal \
  -H "X-Auth-Token: YOUR_TOKEN"
```

---

## Troubleshooting

### Core nicht erreichbar

1. Add-on gestartet?
2. Port `8909` frei?
3. Firewall?

### Keine Sensoren

1. **Entwicklerwerkzeuge** → **Statistiken**
2. Nach `pilotsuite` suchen
3. Coordinator-Logs prüfen

### Dashboard fehlt

1. **Einstellungen** → **Dashboards**
2. Manuell anlegen (siehe oben)

### LLM antwortet nicht

1. **PilotSuite** → **Konfigurieren** → **Self-Heal**
2. Oder: Core Add-on neustarten

---

## Support

- **Issues**: https://github.com/GreenhillEfka/pilotsuite-styx-ha/issues
- **Discord**: (Link im README)
- **Logs**: **Einstellungen** → **System** → **Protokolle** → **PilotSuite**
