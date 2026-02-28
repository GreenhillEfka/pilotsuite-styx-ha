# PilotSuite v11.2 — Live Integrations- und Umsetzungskonzept (SmartHome Andreas)

Stand: 2026-02-27

Dieses Dokument konsolidiert:
- den Ist-Zustand aus **allen Markdown-Dokumenten** in `pilotsuite-styx-ha` und `pilotsuite-styx-core`,
- den realen Live-Stand der Home-Assistant-Instanz,
- den daraus abgeleiteten State-of-the-Art Zielaufbau fuer Architektur, ZeroConfig, Dashboard und neuronale Logik.

## 1) Datengrundlage

### 1.1 Doku-Basis (vollstaendig gescannt)
- HA-Repo: 22 Markdown-Dateien
- Core-Repo: 33 Markdown-Dateien
- Gesamt: 55 Markdown-Dateien

### 1.2 Live-HA Snapshot (2026-02-27)
Quelle: HA API (`/api/states`, `/api/config`, Template-API fuer Areas/Zonen)

- Gesamt-Entities: `4520`
- Areas: `47`
- Zonen: `10`
- Automationen: `110`
- Szenen: `160`
- Media Player: `51`
- Sensoren: `1650`
- Binary Sensoren: `457`
- Climate: `8`

Top-Bereiche nach Entity-Dichte:
- Kontrollraum: 664
- Wohnzimmer: 273
- Arbeitszimmer: 176
- Kueche: 171
- Zimmer Mira: 164
- Schlafzimmer: 156

### 1.3 Code-Basis (Dual Repo)
- HA Version: `11.2.0` (`manifest.json`)
- Core Version: `11.2.0` (`copilot_core/config.yaml`, `VERSION`)
- Git Tag beide Repos: `v11.2.0`

## 2) Verifizierte Unstimmigkeiten aus der historisch gewachsenen Entwicklung

## 2.1 Dokumentations- und Baseline-Drift
Mehrere zentrale Dokumente referenzieren weiterhin `v10.4.0` als aktuelle Baseline, obwohl Runtime bei `v11.2.0` liegt.

Betroffene Kern-Dokumente:
- `INDEX.md` (beide Repos)
- `PROJECT_STATUS.md` (beide Repos)
- `VISION.md` (beide Repos)
- `docs/ROADMAP.md` (Core)
- Teile der Setup-/Architekturtexte

Auswirkung:
- Steuerungsdokumente sind nicht mehr synchron zur Runtime.
- Historie und aktueller Zielzustand verschwimmen.

## 2.2 Tiers vs. reales Modul-Ladeverhalten
Doku beschreibt Tier-Logik als selektiv/profilbasiert, der Bootpfad laedt jedoch weiterhin die gesamte `_MODULES`-Kette standardmaessig.

Auswirkung:
- Erwartete Profilierung (`minimal/standard/full`) ist nicht technisch erzwungen.
- Tier-Semantik ist aktuell eher organisatorisch als runtime-wirksam.

## 2.3 Zone-Source-of-Truth ist gewachsen, aber noch doppelt
Es existieren parallel:
- statische Zonenbasis (`data/zones_config.json`, testrelevant mit 9 Zonen)
- dynamischer ZoneStore (Auto-Setup aus HA Areas, editierbar im Options-Flow)

Auswirkung:
- Produktiv ist dynamisch moeglich, Test-/Fallback-Welt bleibt statisch.
- Ohne klare Export-/Sync-Regel kann Drift zwischen Referenzdatei und Live-Zonen entstehen.

## 2.4 Dashboard-Aussage vs. Datenausnutzung
Die Infrastrukturerkennung war vorhanden, hat aber reale Signale (CO2, Laerm, Media-Dichte) bislang nur teilweise genutzt.

Auswirkung:
- Hoher Informationsgehalt der realen Instanz wurde im Hausverwaltungs-Tab nicht voll ausgespielt.

## 2.5 Neuronale Mathe/Callback-Konsistenz
Im Neuron-Manager war die proaktive Suggestion-Weiterleitung auf ein altes Single-Callback-Attribut verdrahtet; Mood-Confidence war nicht als normierte Verteilung abgesichert.

Auswirkung:
- Callback-Inkonsistenzen in Tests/Integrationen.
- Confidence-Werte waren nicht sauber vergleichbar zwischen unterschiedlichen Mood-Vektoren.

## 3) Zielbild v11.2 -> v12.0

## 3.1 Produktkern (Dual-Repo Contract-First)
- Core = Entscheidungs-, Pipeline-, API- und Governance-Backend.
- HA = Runtime-Integration, ZeroConfig, Entitaetenabbildung, Bedien- und Freigabeflaeche.
- Gemeinsamer Contract fuer:
  - Zonen
  - Suggestionen
  - Mood-/Neuron-Status
  - Dashboard-Snapshots

## 3.2 ZeroConfig 2.0 (live-entity-first)
Ziel: Nach abgeschlossenem ZeroConfig-Flow liegt automatisch eine nutzbare, echte Grundkonfiguration vor.

Soll-Ablauf:
1. HA Areas + Entitaeten einlesen.
2. Rollenklassifikation (motion/lights/heating/co2/noise/media/power/...).
3. Habitus-Zonen im Store erzeugen.
4. Entity-Tags automatisch setzen (`aicp.place.*` + Domaintags).
5. Backend-Reiter **Zonen** als primare Editierflaeche fuer Feintuning.
6. Vollsync an Core + Dashboard-Regeneration.

## 3.3 Dashboard UX (state of the art, high-density)

### Habitus
- Mood-Gauges
- Zone-Grid mit Umwelt-Headern
- Personenstatus
- Luftqualitaetsverlauf (CO2/Laerm, sofern vorhanden)
- Temperaturhistorie

### Hausverwaltung
- Kompakte Zonenuebersicht
- Dynamische Sektionen: Energie, Heizung, CO2, Laerm, Sicherheit, Medien/Player, Netzwerk, Wetter
- Verlaufsgrafen fuer Energie und CO2/Laerm
- Geraeteblock als Bedienflaeche

### Styx
- Neural-Pipeline
- Brain-Graph
- Mood-Verlauf
- Vorschlagsqueue + Aktionen + Systemstatus

## 3.4 Neuronale Mathe und Modullogik
- Mood-Scores robust auf `[0..1]` clampen.
- Dominante Stimmung aus **normalisierter Verteilung** bestimmen (vergleichbare Confidence).
- Historienglaettung beibehalten (kurzes Fenster), aber nur mit validierten Werten.
- Proaktive Suggestionen immer ueber das Multi-Callback-Modell dispatchen.

## 4) Bereits umgesetzte Verbesserungen in diesem Schritt

## 4.1 Core
- `neurons/manager.py`
  - Legacy Callback-Kompatibilitaet wiederhergestellt (`_on_mood_change`, `_on_suggestion` Alias)
  - Proaktive Suggestionen sauber ueber alle registrierten Suggestion-Callbacks verteilt
  - Mood-Confidence mathematisch stabilisiert (Clamp + Normalisierung)
- Tests erweitert (`test_neural_system.py`):
  - Confidence-Normalisierung
  - Proaktive Callback-Weiterleitung

## 4.2 HA
- `dashboard_pipeline.py`
  - Infrastruktur-Erkennung erweitert um `media`, `co2`, `noise`
  - bessere Klassifikationsheuristik + deduplizierte/sortierte Kategorien
- `pilotsuite_3tab_generator.py`
  - Habitus: CO2/Laerm im Zone-Header, Luftqualitaets-History
  - Hausverwaltung: dynamische CO2/Laerm/Media-Sektionen, Verlaufsgrafen, Zonenuebersicht
  - `generate_hausverwaltung_tab(..., zones=...)` fuer konsolidierte Darstellung
- Tests erweitert (`test_dashboard_pipeline.py`) fuer neue Kategorien

## 5) Konsolidierte Vorgehensmethode (empfohlen)

1. **Contract + Docs Freshness als harte Gates**
- Release failt bei Version-/Baseline-Drift in Kern-Dokumenten.
- Contract-Tests blockieren unversionierte API-Aenderungen.

2. **Runtime-Profilierung technisch durchsetzen**
- Modulmanifeste pro Modul
- Profile `minimal|standard|full|experimental`
- echter Loader statt nur dokumentierter Tier-Logik

3. **Zone Source-of-Truth klarziehen**
- ZoneStore als operative Wahrheit
- statische `zones_config.json` als fallback/test fixture
- definierter Exportpfad fuer reproduzierbare Beispielkonfigurationen

4. **Dashboard nach Datenprioritaet statt starrer Sektionen**
- zuerst reale Signale mit hohem Nutzen (CO2/Laerm/Heizung/Media/Energie)
- dann statische Kompatibilitaetskarten

5. **Mathematische Qualitaet messen**
- Mood-Confidence-Verteilung monitoren
- Suggestion-Akzeptanzrate je Mood/Zone
- Suppression-Falschpositive als KPI

## 6) Kurzfristige Umsetzung (naechste 2 Wochen)

Woche 1:
- Docs-Drift in `VISION/INDEX/PROJECT_STATUS/ROADMAP` aufloesen
- docs-freshness CI in beiden Repos aktivieren
- ZoneStore-Exportservice einfuehren (generated config)

Woche 2:
- Contract-Schemas fuer Zonen/Suggestions/Mood finalisieren
- Producer/Consumer Tests in beiden Repos scharf schalten
- Dashboard-Priorisierung anhand echter Live-Daten feinjustieren

## 7) Erwartetes Ergebnis

- ZeroConfig liefert sofort eine real nutzbare, editierbare Grundkonfiguration auf echten Entitaeten.
- Dashboard zeigt hohe Informationsdichte ohne Redundanz.
- Dual-Repo bleibt release-faehig ohne Doku-/Contract-Drift.
- Neuronales System liefert stabilere, besser interpretierbare Confidence-Werte.
