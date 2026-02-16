# AI Home CoPilot - Benutzerhandbuch

> **Version:** Integration v0.13.4 + Core Add-on v0.8.7
> **Letzte Aktualisierung:** 2026-02-16

---

## Inhaltsverzeichnis

1. [Was ist AI Home CoPilot?](#was-ist-ai-home-copilot)
2. [Systemvoraussetzungen](#systemvoraussetzungen)
3. [Installation Core Add-on](#installation-core-add-on)
4. [Installation HACS Integration](#installation-hacs-integration)
5. [Erstkonfiguration](#erstkonfiguration)
6. [Zonen einrichten](#zonen-einrichten)
7. [Module und Features](#module-und-features)
8. [Dashboard-Karten](#dashboard-karten)
9. [API-Referenz](#api-referenz)
10. [Fehlerbehebung](#fehlerbehebung)

---

## Was ist AI Home CoPilot?

Ein **privacy-first, lokaler KI-Assistent** fuer Home Assistant. CoPilot lernt die Muster deines Zuhauses und schlaegt intelligente Automatisierungen vor. Alle Daten bleiben lokal - kein Cloud-Dependency. Der Mensch entscheidet immer.

**Architektur:** Zwei Komponenten arbeiten zusammen:

| Komponente | Beschreibung | Port |
|------------|-------------|------|
| **Core Add-on** | Flask-basierter Backend-Server mit Brain Graph, Neuronen, Energy-Analyse | 8099 |
| **HACS Integration** | Home Assistant Custom Component mit 80+ Sensoren, Zonen, Media Context | - |

```
Home Assistant
  |
  +-- HACS Integration (custom_components/ai_home_copilot)
  |     Sensoren, Entities, Event-Forwarder, Zonen
  |     |
  |     +--[ HTTP / Webhook ]--> Core Add-on (:8099)
  |                                Brain Graph, Neuronen, Energy
  |                                Habitus Miner, Candidates, Tags
  +-- Lovelace Dashboard
        Zone Context, Brain Graph Viz, Mood Tracker
```

---

## Systemvoraussetzungen

- Home Assistant OS oder Supervised (>= 2024.1)
- HACS installiert (fuer die Integration)
- Min. 2 GB freier RAM (empfohlen: 4 GB)
- Netzwerkzugang zwischen HA und Core Add-on (Port 8099)

---

## Installation Core Add-on

### Schritt 1: Repository hinzufuegen

1. **Home Assistant** -> **Einstellungen** -> **Add-ons**
2. **Add-on Store** (drei Punkte) -> **Repositories**
3. Repository-URL eingeben: `https://github.com/GreenhillEfka/Home-Assistant-Copilot`

### Schritt 2: Add-on installieren

1. **Copilot Core** im Add-on Store finden
2. **Installieren** klicken
3. Warten bis Installation abgeschlossen

### Schritt 3: Konfigurieren

Add-on Konfiguration bearbeiten:

```yaml
log_level: info
auth_token: dein-geheimes-token-hier-aendern
port: 8099
```

| Parameter | Standard | Beschreibung |
|-----------|----------|--------------|
| `port` | `8099` | HTTP-Port fuer die API |
| `auth_token` | (Pflicht) | Geheimes Token fuer Authentifizierung |
| `log_level` | `info` | Log-Level: debug, info, warning, error |
| `storage_path` | `/data` | Pfad fuer persistente Daten |
| `max_nodes` | `500` | Max. Knoten im Brain Graph |
| `max_edges` | `1500` | Max. Kanten im Brain Graph |

### Schritt 4: Starten und pruefen

1. **Start** im Add-on klicken
2. Logs pruefen:

```bash
# Health Check
curl http://homeassistant.local:8099/health
# -> {"ok": true}

# Version
curl http://homeassistant.local:8099/version
# -> {"version": "0.8.7"}
```

---

## Installation HACS Integration

### Schritt 1: Via HACS installieren

1. **HACS** oeffnen -> **Integrationen**
2. Nach **AI Home CoPilot** suchen
3. **Herunterladen** klicken

### Schritt 2: Integration konfigurieren

1. **Einstellungen** -> **Geraete & Dienste** -> **Integration hinzufuegen**
2. Nach **AI Home CoPilot** suchen
3. Konfigurieren:
   - **Core URL:** `http://homeassistant.local:8099`
   - **Auth Token:** (gleiches Token wie im Core Add-on)

### Schritt 3: Home Assistant neu starten

Nach dem Neustart erscheinen 80+ Entitaeten unter `ai_home_copilot.*`.

---

## Erstkonfiguration

### Wichtige Einstellungen

Nach der Installation in **Einstellungen** -> **Geraete & Dienste** -> **AI Home CoPilot** -> **Konfigurieren**:

| Bereich | Einstellung | Empfehlung |
|---------|------------|------------|
| **Verbindung** | Host, Port, Token | Muss mit Core uebereinstimmen |
| **Media Player** | Musik/TV Player-Listen | Alle relevanten Player eintragen |
| **Events Forwarder** | Aktiviert, Flush-Intervall | `true`, 30s |
| **Neuronen** | Aktiviert, Evaluierungs-Intervall | `true`, 60s |
| **Watchdog** | Aktiviert, Intervall | `true`, 300s |
| **Devlog Push** | Aktiviert | Optional, fuer Debugging |

### Umgebungsvariablen (Erweitert)

| Variable | Beschreibung |
|----------|-------------|
| `COPILOT_AUTH_TOKEN` | Auth-Token Override |
| `COPILOT_AUTH_REQUIRED` | Auth an/aus (Standard: true) |
| `COPILOT_TAG_ASSIGNMENTS_PATH` | Pfad fuer Tag-Zuweisungen |
| `COPILOT_VECTOR_DB_PATH` | Pfad fuer Vector Store DB |
| `COPILOT_USE_OLLAMA` | Ollama fuer Embeddings nutzen |
| `COPILOT_OLLAMA_MODEL` | Ollama Modell (Standard: nomic-embed-text) |
| `COPILOT_OLLAMA_URL` | Ollama Server URL |

---

## Zonen einrichten

### Zonen-Hierarchie

CoPilot nutzt eine hierarchische Zonenstruktur:

```
Etage (floor)
  -> Bereich (area)
    -> Raum (room)
```

**Beispiel:**

```
EG (floor)
  +-- Wohnbereich (area)
  |     +-- Wohnzimmer (room)
  |     +-- Kueche (room)
  +-- Schlafbereich (area)
        +-- Schlafzimmer (room)
        +-- Bad (room)
```

### Zonen via YAML erstellen

```yaml
zones:
  - name: EG
    type: floor
    children:
      - name: Wohnbereich
        type: area
        children:
          - name: Wohnzimmer
            type: room
            roles:
              lights: light.wohnen_*
              motion: binary_sensor.motion_wohnen
              temperature: sensor.temperature_wohnen
              media: media_player.wohnbereich
```

### Entity-Rollen

| Rolle | Entitaeten | Pflicht |
|-------|-----------|---------|
| `motion` | Bewegungsmelder | Ja (mind. 1) |
| `lights` | Lampen | Ja (mind. 1) |
| `temperature` | Temperatursensoren | Nein |
| `humidity` | Feuchtigkeitssensoren | Nein |
| `co2` | CO2-Sensoren | Nein |
| `heating` | Thermostate | Nein |
| `door` / `window` | Tuer-/Fenstersensoren | Nein |
| `media` | Media Player | Nein |
| `power` / `energy` | Strom-/Energiemonitore | Nein |

### Zonen-Zustaende

| Zustand | Bedeutung |
|---------|-----------|
| `idle` | Keine Aktivitaet |
| `active` | Person anwesend |
| `occupied` | Raum belegt |
| `sleeping` | Schlafmodus |
| `transitioning` | Zustandswechsel |
| `disabled` | Zone deaktiviert |

---

## Module und Features

### Core Add-on Module

#### Brain Graph
Wissens-Graph der Entity-Beziehungen mit zeitbasiertem Score-Decay.

- **Funktion:** Verfolgt Beziehungen zwischen Entitaeten, Zonen und Mustern
- **Konfiguration:** `max_nodes` (500), `max_edges` (1500), `node_half_life_hours` (24)
- **API:** `GET /api/v1/graph/state`, `POST /api/v1/graph/link`

#### Neuronen-System
Kontextneuronen bewerten den Zustand des Hauses.

- **Kontext-Neuronen:** Praesenz, Tageszeit, Lichtlevel, Wetter, Netzwerk
- **Zustands-Neuronen:** Energielevel, Stress-Index, Routine-Stabilitaet, Komfort
- **Mood-Neuronen:** Relax, Focus, Active, Sleep, Away, Alert, Social
- **API:** `GET /api/v1/neurons/state`, `GET /api/v1/mood/current`

#### Energy-Modul
Energiemonitoring mit Anomalie-Erkennung und Lastverschiebung.

- **Funktion:** Anomalie-Erkennung, PV-Prognose, Shifting-Empfehlungen
- **Schwellwerte:** low (15%), medium (30%), high (50%)
- **API:** `GET /api/v1/energy/snapshot`, `GET /api/v1/energy/anomalies`

#### Habitus Miner
Mustererkennung aus State History fuer Automatisierungs-Vorschlaege.

- **Funktion:** Entdeckt wiederkehrende Muster (z.B. "Morgens um 7: Kueche Licht an")
- **Parameter:** `min_confidence` (0.5), `min_support` (5), `max_delta_seconds` (3600)
- **API:** `GET /api/v1/habitus/rules`

#### Candidates
Lebenszyklus-Management fuer Automatisierungs-Vorschlaege.

- **Zustaende:** pending -> offered -> accepted/dismissed/deferred
- **API:** `GET /api/v1/candidates`, `POST /api/v1/candidates/{id}/accept`

#### Tag-System v2
Hierarchisches Tag-System mit HA-Label-Materialisierung.

- **Facetten:** role, state, location, device_type, custom
- **API:** `GET /api/v1/tags`, `POST /api/v1/assignments`

#### Vector Store
Embedding-basierte Aehnlichkeitssuche fuer Entitaeten und Muster.

- **Backend:** SQLite mit optionalem Ollama fuer Embeddings
- **API:** `POST /api/v1/vector/search`, `POST /api/v1/vector/upsert`

#### UniFi-Integration
Netzwerk-Monitoring fuer WAN-Status und Client-Roaming.

- **Funktion:** WAN-Status, Latenz, Paketverlust, Traffic-Baselines
- **API:** `GET /api/v1/unifi/snapshot`

#### Log Fixer TX
Transaktionslog (WAL) fuer Konfigurationsaenderungen mit Rollback.

- **Funktion:** Sichere Konfigurationsaenderungen mit Undo-Moeglichkeit
- **Zustaende:** INTENT -> APPLIED / FAILED / ROLLED_BACK

#### Dev Surface
Entwickler-Observability mit strukturiertem Logging.

- **Funktion:** Ring-Buffer Logging, Error-Tracking, System-Health
- **API:** `GET /api/v1/dev/logs`, `GET /api/v1/dev/health`

#### Collective Intelligence
Foederiertes Lernen ueber mehrere Haeuser mit Privacy-Erhaltung.

- **Funktion:** Wissenstransfer zwischen Instanzen (opt-in)
- **Privacy:** Differential Privacy mit epsilon=1.0

### HACS Integration Module

#### Event Forwarder (forwarder_n3)
Leitet HA-Events an den Core Add-on weiter.

- **Funktion:** Persistent Queue, Batch-Versand, Idempotency
- **Config:** `flush_interval` (30s), `max_batch` (100), `queue_size` (10000)

#### Media Context v2
Erweiterte Medien-Kontexterkennung mit Zonen-Mapping.

- **Funktion:** Aktiver Modus (TV/Musik/Mixed), Zonen-Routing, Lautstaerke-Steuerung
- **Sensoren:** Active Mode, Active Target, Active Zone, Config Validation

#### Habitus Zones v2
Erweiterte Zonen-Verwaltung mit Hierarchie und Brain-Graph-Integration.

- **Funktion:** Zonen-Hierarchie, Zustandsmaschine, Prioritaeten, Konfliktloesung
- **Sensoren:** Zone Count, Zone States, Zone Health, Global State Select

#### Neuron Dashboard
Dashboard-Sensoren fuer das Neuronen-System.

- **Sensoren:** Mood, Confidence, Activity Level, Suggestions, History

#### Energy Insights
Energie-Einsichten und Empfehlungen.

- **Sensoren:** Current Insights, Recommendations, PV Forecast

#### Multi-User Preferences (MUPL)
Mehrbenutzer-Praeferenz-Lernen.

- **Funktion:** Privacy-bewusstes Lernen von Nutzervorlieben
- **Config:** `privacy_mode`, `min_interactions`, `retention_days`

#### Diagnostics
Diagnosebericht-Erstellung fuer Fehlerbehebung.

- **Funktion:** Exportiert vollstaendigen Systembericht ueber HA Diagnostics

---

## Dashboard-Karten

### Verfuegbare Karten

| Karte | Zweck |
|-------|-------|
| Zone Context | Zonen-Uebersicht mit Entity-Zustaenden |
| Brain Graph | Neuronale Visualisierung |
| Mood Tracker | Stimmungsverlauf |
| Energy Distribution | Energieverbrauch |
| Habitus Rules | Entdeckte Automatisierungsregeln |
| Tag Browser | Tag-Verwaltung |

### Beispiel: Zone Context Card

```yaml
type: custom:ai-home-copilot-zone-context
title: Wohnzimmer
zone: wohnzimmer
show_roles:
  - lights
  - temperature
  - motion
```

### Beispiel: Brain Graph Card

```yaml
type: custom:ai-home-copilot-brain-graph
title: Home Neural Network
center: zone.wohnzimmer
hops: 2
theme: dark
layout: dot
```

---

## API-Referenz

Der Core Add-on stellt eine REST API auf Port 8099 bereit.

### Authentifizierung

Alle API-Anfragen benoetigen den Header:
```
Authorization: Bearer <auth_token>
```

### Wichtigste Endpunkte

| Methode | Pfad | Beschreibung |
|---------|------|-------------|
| `GET` | `/health` | Health Check |
| `GET` | `/version` | Versionsinformation |
| `GET` | `/api/v1/status` | Systemstatus |
| `GET` | `/api/v1/capabilities` | Verfuegbare Module |
| `POST` | `/api/v1/events` | Events einliefern |
| `GET` | `/api/v1/events` | Events auflisten |
| `GET` | `/api/v1/graph/state` | Brain Graph Zustand |
| `GET` | `/api/v1/neurons/state` | Neuronen-Zustand |
| `GET` | `/api/v1/mood/current` | Aktueller Mood |
| `GET` | `/api/v1/habitus/rules` | Habitus-Regeln |
| `GET` | `/api/v1/candidates` | Automatisierungs-Vorschlaege |
| `GET` | `/api/v1/tags` | Tags auflisten |
| `GET` | `/api/v1/assignments` | Tag-Zuweisungen |
| `GET` | `/api/v1/energy/snapshot` | Energie-Snapshot |
| `GET` | `/api/v1/unifi/snapshot` | UniFi-Snapshot |
| `GET` | `/api/v1/vector/search` | Vector-Suche |
| `GET` | `/api/v1/dev/logs` | Dev-Logs |
| `GET` | `/api/v1/dev/health` | System-Health |

Vollstaendige API-Dokumentation: `http://homeassistant.local:8099/api/v1/docs/`

---

## Fehlerbehebung

### Core Add-on startet nicht

```bash
# Logs pruefen (in HA Add-on Ansicht)
# Haeufige Probleme:
# - Port 8099 bereits belegt
# - Ungültiges Auth-Token
# - Fehlende Abhaengigkeiten
```

### Integration findet Core nicht

1. Core laeuft pruefen: `curl http://<HA_IP>:8099/health`
2. Firewall erlaubt Port 8099
3. Auth-Token stimmt ueberein

### Entitaeten erscheinen nicht

1. **Entwicklerwerkzeuge** -> **Zustaende**
2. Nach `ai_home_copilot.*` suchen
3. Integration neu starten

### Brain Graph leer

- 5-10 Min. auf initiale Daten warten
- Pruefen ob Events weitergeleitet werden
- Core Events pruefen: `GET /api/v1/events?limit=5`

### Zonen-Zustaende falsch

- Entity-Rollen-Zuweisungen pruefen
- Sensoren funktionieren in HA
- Zonen-Hierarchie (Parent/Child) korrekt

### Tests ausfuehren

```bash
# Core Add-on Tests (521 Tests)
cd addons/copilot_core/rootfs/usr/src/app
python3 -m pytest tests/ copilot_core/neurons/test_neurons.py --ignore=tests/test_knowledge_graph.py

# HACS Integration Tests (346 Tests)
cd custom_components/ai_home_copilot
python3 -m pytest tests/
```

---

*Letzte Aktualisierung: 2026-02-16*
