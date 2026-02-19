# PilotSuite -- Installations- und Benutzerhandbuch

> Deutsches Handbuch fuer Installation, Konfiguration und Nutzung der PilotSuite-Plattform (Core Add-on + HACS Integration).

---

## Inhaltsverzeichnis

1. [Voraussetzungen](#1-voraussetzungen)
2. [Installation](#2-installation)
3. [Erstkonfiguration](#3-erstkonfiguration)
4. [Moduluebersicht](#4-moduluebersicht)
5. [Troubleshooting](#5-troubleshooting)

---

## 1. Voraussetzungen

### Hardware

- Home Assistant OS oder Supervised Installation (Add-on Support erforderlich)
- Mindestens 1 GB freier RAM fuer das Core Add-on
- Netzwerkzugang (LAN, kein Internet erforderlich)

### Software

- **Home Assistant** 2024.1 oder neuer
- **HACS** (Home Assistant Community Store) installiert -- siehe https://hacs.xyz
- **Supervisor** aktiv (fuer Add-on Installation)

### Optionale Integrationen

- UniFi Controller (fuer Netzwerk-Ueberwachung)
- PV-Anlage / Energiesensoren (fuer Energiemonitoring)
- Media Player Entities (fuer Medien-Kontext)
- Person/Device-Tracker Entities (fuer Anwesenheitserkennung)

---

## 2. Installation

### 2.1 Core Add-on installieren

1. In Home Assistant: **Settings** > **Add-ons** > **Add-on Store**
2. Menue (drei Punkte) > **Repositories**
3. Diese URL hinzufuegen:
   ```
   https://github.com/GreenhillEfka/Home-Assistant-Copilot
   ```
4. **PilotSuite Core** (AI Home CoPilot Core) suchen und installieren
5. Add-on starten
6. Pruefen ob das Add-on laeuft: `http://<ha-ip>:8909/health`

Das Add-on laeuft auf Port **8909** und erwartet keine weitere Konfiguration fuer den Grundbetrieb.

### 2.2 HACS Integration installieren

1. HACS oeffnen > **Integrations**
2. Menue (drei Punkte) > **Custom repositories**
3. Repository-URL hinzufuegen:
   ```
   https://github.com/GreenhillEfka/ai-home-copilot-ha
   ```
   Typ: **Integration**
4. **AI Home CoPilot** ueber HACS installieren
5. Home Assistant **neustarten**

### 2.3 Integration einrichten

1. **Settings** > **Devices & services** > **Add integration**
2. **AI Home CoPilot** suchen und auswaehlen
3. Konfiguration ausfuellen:

| Feld | Standard | Beschreibung |
|------|----------|-------------|
| Host | `homeassistant.local` | IP-Adresse oder Hostname |
| Port | `8909` | Core Add-on Port |
| API Token | (leer) | Optional: Shared Token fuer Authentifizierung |

---

## 3. Erstkonfiguration

### 3.1 auth_token (Optional)

Fuer zusaetzliche Sicherheit kann ein gemeinsamer Token konfiguriert werden:

1. **Core Add-on**: In `/data/options.json` den Wert `auth_token` setzen, oder die Umgebungsvariable `COPILOT_AUTH_TOKEN` definieren
2. **HACS Integration**: Den gleichen Token im Setup-Dialog oder Options-Flow eingeben

Ohne Token sind alle API-Endpoints frei zugaenglich (nur im lokalen Netzwerk empfohlen).

### 3.2 Household-Konfiguration

Das Household-Modul ermoeglicht altersgerechte Empfehlungen:

1. **Settings** > **Devices & services** > **AI Home CoPilot** > **Configure**
2. Im Options-Flow **Household** waehlen
3. Familienmitglieder anlegen mit Name und Altersgruppe:
   - Kleinkind (0-5 Jahre)
   - Kind (6-12 Jahre)
   - Jugendlicher (13-17 Jahre)
   - Erwachsener (18-64 Jahre)
   - Senior (65+ Jahre)

### 3.3 Habitus Zones

Zonen definieren, in denen Verhaltensmuster erkannt werden:

1. Im Options-Flow **Habitus Zones** waehlen
2. Zonen aus vorhandenen HA Areas erstellen
3. Entities den Zonen zuordnen

Standard-Zonen: Wohnbereich, Kochbereich, Schlafbereich, Badbereich, Gangbereich, Terrassenbereich.

### 3.4 Events Forwarder

Konfiguriert welche Events an das Core Add-on weitergeleitet werden:

- **Habitus Zones**: Entities aus konfigurierten Zonen (Standard: aktiv)
- **Media Players**: Konfigurierte Musik- und TV-Player (Standard: aktiv)
- **Zusaetzliche Entities**: Weitere Entity-IDs als CSV-Liste

---

## 4. Moduluebersicht

### Brain Graph

Der Wissensgraph speichert Beziehungen zwischen Entities, Zonen und Devices. Er bildet die Grundlage fuer Pattern-Erkennung.

- Automatische Synchronisation mit dem Core Add-on
- Interaktive D3.js Visualisierung als Dashboard Card
- Max. 500 Nodes und 1500 Edges (konfigurierbar)

### Habitus Miner

Erkennt wiederkehrende Verhaltensmuster:

- Zeitbasierte Muster ("Jeden Morgen um 7:00 geht das Licht an")
- Trigger-basierte Muster ("Wenn die Tuer oeffnet, geht das Licht an")
- Sequenzielle Muster ("Erst TV an, dann Licht dimmen")
- Kontextuelle Muster ("Bei Regen Rolladen schliessen")

### Mood Engine

Multidimensionale Stimmungsbewertung pro Zone:

- **Comfort**: Wohlfuehl-Faktor (Temperatur, Licht, Luft)
- **Joy**: Unterhaltungs-Faktor (Medien, Aktivitaet)
- **Frugality**: Sparsamkeits-Faktor (Energieverbrauch)

### Candidate System

Vorschlaege fuer Automatisierungen:

1. Core erkennt Muster (Habitus Mining)
2. Kandidat wird erstellt mit Konfidenz-Wert
3. HACS Integration zeigt Vorschlag in HA Repairs UI
4. Nutzer akzeptiert, verschiebt oder verwirft
5. Entscheidung wird an Core zurueckgemeldet (Feedback Loop)

### Household-Modul

Familienkonfiguration mit altersgerechten Empfehlungen:

- Bettzeit-Empfehlungen basierend auf juengster Altersgruppe
- Anpassung von Vorschlaegen an Familienzusammensetzung
- Multi-User Stimmungs-Tracking

### Home Alerts

Ueberwachung kritischer Zustaende:

- Batterien (niedrig), Klima (Temperatur ausserhalb Bereich)
- Anwesenheit (unerwartete Abwesenheit), System (Add-on Status)
- Health Score (0-100)

---

## 5. Troubleshooting

### Core Add-on startet nicht

1. Logs pruefen: **Settings** > **Add-ons** > **PilotSuite Core** > **Log**
2. Port-Konflikt pruefen: Port 8909 muss frei sein
3. Speicherplatz pruefen: Add-on benoetigt Schreibzugriff auf `/data/`

### Integration verbindet sich nicht

1. Core Add-on Health-Check: `http://<ha-ip>:8909/health`
   - Erwartet: `{"ok": true, ...}`
2. Host/Port in Integration-Konfiguration pruefen
3. Token pruefen (muss in beiden Konfigurationen identisch sein)
4. Firewall-Regeln pruefen (Port 8909 muss erreichbar sein)

### Sensoren zeigen "unavailable"

1. Core Add-on Status pruefen (muss laufen)
2. Integration neu laden: **Settings** > **Integrations** > **AI Home CoPilot** > **Reload**
3. Logs filtern nach `ai_home_copilot` fuer detaillierte Fehlermeldungen

### Keine Vorschlaege werden angezeigt

1. Events Forwarder muss aktiv sein
2. Mindestens 24-48 Stunden Datensammlung abwarten
3. Habitus Zones muessen konfiguriert sein
4. Mining manuell ausloesen: Service `ai_home_copilot.trigger_mining`

### Performance-Probleme

1. Events Forwarder Batch-Groesse reduzieren
2. Polling-Intervalle erhoehen
3. Anzahl ueberwachter Entities reduzieren
4. Debug-Level auf "off" setzen

---

*Letzte Aktualisierung: 2026-02-16 -- PilotSuite Alpha Release*
