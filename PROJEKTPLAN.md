# PilotSuite Styx - Projektplan (Update 2026-02-27)

## Baseline (verifiziert)

- Dual-Repo Release-Stand: **HA v11.2.0** und **Core v11.2.0**
- HA Runtime-Module im Bootpfad (`__init__._MODULES`): **39**
- Core Services in `core_setup.py` (services-Dict Keys): **31**
- Testsammlung (lokal `pytest --collect-only`): **883 (HA)** + **2351 (Core)**
- Production Guard in beiden Repos aktiv (Cron alle 15 Minuten)

Dieses Dokument ersetzt den alten v10.4.0-Abschlussplan als aktiven Umsetzungsplan.

---

## Live-HA Reality Check (2026-02-27)

Verifizierter Snapshot aus der echten Instanz (API):

- Entities gesamt: **4520**
- Areas: **47**
- Zonen: **10**
- Automationen: **110**
- Szenen: **160**
- Media Player: **51**
- Sensoren: **1650**
- Binary Sensoren: **457**
- Climate: **8**

Top-Bereiche nach Entitaetsdichte:
- Kontrollraum (664), Wohnzimmer (273), Arbeitszimmer (176), Kueche (171), Zimmer Mira (164)

Konsequenz fuer den Plan:
- Fokus auf **live-entity-first** statt statischer Beispielwelten.
- ZeroConfig muss reproduzierbar aus echten Areas/Entitaeten eine editierbare Startkonfiguration liefern.

---

## Kern der Vision (bleibt unveraendert)

- Local-first
- Privacy-first
- Governance-first (Vorschlag vor Aktion)
- Explainability und reproduzierbares Verhalten
- Graceful degradation bei Teil-Ausfaellen

---

## Verifizierte Unstimmigkeiten (historisch gewachsen)

### 1) Doku-Drift zwischen "aktueller Stand" und Realitaet

- Mehrere zentrale Dateien sprechen noch von `v10.4.0` oder `v9.0.0` als Baseline, obwohl Code auf `v11.2.0` steht.
- `INDEX.md` (beide Repos) zeigt noch "Current release: v10.4.0".
- `RELEASE_NOTES.md` endet bei `v10.1.5`, waehrend `CHANGELOG.md` bereits `v11.2.0` dokumentiert.
- `VISION.md`, `PROJECT_STATUS.md`, `ROADMAP.md`, Setup-Guides und Architekturdokumente nutzen teils widerspruechliche Kennzahlen.

### 2) Tier-Konzept vs. technisches Ladeverhalten

- Doku beschreibt Tier-2/Tier-3 als bedingt/optional.
- Realer Bootpfad laedt aktuell die komplette `_MODULES`-Liste (39 Eintraege) ohne vorgelagerte Tier-Gating-Logik.

### 3) Core-Bootpfad mit Drift-Risiko

- Es existieren zwei relevante Entry-Point-Welten:
  - `main.py` (Produktion, `core_setup.init_services/register_blueprints`)
  - `copilot_core/app.py` (Factory fuer Tests/Lightweight)
- Risiko: Testpfad und produktiver Pfad koennen auseinanderlaufen.

### 4) API-Topologie inkonsistent gewachsen

- Mischung aus relativen und absoluten Blueprint-Prefixes.
- Historisch additiv gewachsene API-Flaechen ohne klar sichtbare "single registry of truth" fuer Contracts.

### 5) Strukturelle Monolith-Bereiche

- Sehr grosse Einzeldateien erschweren Wartung/Onboarding/saubere Trennung:
  - `core_setup.py` (~1190)
  - `api/v1/conversation.py` (~2352)
  - `hub/api.py` (~3392)
  - HA `__init__.py` (~777), `coordinator.py` (~829), `sensor.py` (~1487)

---

## Zielbild (State-of-the-Art, v11.2 -> v12.0)

### Architekturziel

- Ein klarer, testbarer **Dual-Repo Contract** als Produktkern (Schemas + kompatible API-Lebenszyklen).
- **Single Source of Truth** fuer Version/Baseline/Status/Roadmap.
- **Einheitlicher Core-Bootpfad** (gleiche Wiring-Logik fuer Produktion und Tests).
- **Modul-Lifecycle mit echten Runtime-Profilen** statt rein dokumentarischer Tiers.
- Refactoring in kleine, austauschbare Komponenten (Strangler Pattern, keine Big-Bang-Rewrites).

### Betriebsziel

- Jede Release-Aussage ist automatisiert belegbar (Tests, Version, Docs-Freshness, Contract-Checks).
- Kein Shipping von Architektur-/Versionsdrift.

---

## Umsetzungs- und Implementierungsplan

## Phase 0 - Governance Reset (1 Woche)

### Scope

- Dokumentations-Governance und "Source-of-truth" festziehen.

### Deliverables

- Eine kanonische Version/Baseline-Datei pro Repo (maschinell auslesbar).
- Regel: `VISION.md`, `INDEX.md`, `PROJECT_STATUS.md`, `PROJEKTPLAN.md` werden bei Release gemeinsam aktualisiert.
- CI-Check "docs-freshness": fail bei Baseline-Drift (Versionen, Release-Hinweise, Statusdaten).

### Exit-Kriterien

- Kein zentrales Dokument verweist mehr auf v10.4.0 als aktuellen Stand.
- Release Notes und Changelog sind synchron (gleiche letzte Version).

## Phase 1 - Contract-First Dual Repo (2 Wochen)

### Scope

- API- und Payload-Contracts zwischen HA und Core vereinheitlichen.

### Deliverables

- Gemeinsame Contract-Schemas fuer kritische Fluesse:
  - Events ingest
  - Candidates pull/update
  - Mood/Neuron webhook payloads
  - Module status snapshots
- Versionierte Compatibility-Matrix (n/n-1 support policy).
- Contract-Tests in beiden Repos (Producer/Consumer).

### Exit-Kriterien

- Breaking changes ohne Contract-Update blockieren CI.
- Paired release validation ist automatisiert.

## Phase 2 - Core Boot-Unification (2-3 Wochen)

### Scope

- Produktions- und Test-Bootpfad angleichen.

### Deliverables

- Gemeinsamer App-Factory-Kern, der von `main.py` und Tests genutzt wird.
- Blueprint-Registrierung ueber ein zentrales Registry-Modell (inkl. Metadaten).
- Sichtbarer API-Index aus der Registry generiert.

### Exit-Kriterien

- Kein Endpoint "nur in einem Pfad" ohne explizite Markierung und Test.
- Smoke-Tests laufen gegen denselben Wiring-Stack.

## Phase 3 - HA Modul-Lifecycle Realignment (2-3 Wochen)

### Scope

- Tier-Modell technisch wahr machen.

### Deliverables

- Modul-Manifest pro Modul: Tier, prerequisites, default_profile, healthcheck.
- Runtime-Profile:
  - `minimal`
  - `standard`
  - `full`
  - `experimental`
- Echte Loader-Policy statt pauschalem `_MODULES` Start.
- Options-Flow auf neues Profil-/Modellayout umstellen.

### Exit-Kriterien

- Dokumentierte Tier-Regeln entsprechen gemessenem Ladeverhalten.
- Startup-Zeit und Fehlerrate pro Profil messbar.

## Phase 4 - Codebase Entflechtung & Qualitaet (laufend, 4+ Wochen)

### Scope

- Monolith-Dateien in klar abgegrenzte Subsysteme zerlegen.

### Deliverables

- `conversation.py`, `core_setup.py`, `hub/api.py`, HA `sensor.py` in feature-nahe Module splitten.
- Shared utilities extrahieren (validation, auth adapters, response shaping, error envelopes).
- Performance- und Observability-Budgets pro kritischem Endpoint.

### Exit-Kriterien

- Keine neue Datei >700 LOC ohne ADR-Ausnahme.
- Kritische Endpunkte mit P95/P99 Telemetrie in CI-Smoke.

## Phase 5 - Intelligence & Product Hardening (parallel ab Phase 2)

### Scope

- Visiontreue KI-Funktionalitaet mit messbarer Qualitaet.

### Deliverables

- Bewertungs-Harness fuer Vorschlagsqualitaet (precision of suggestions, suppression correctness, acceptance ratio).
- Klare Trennung von "informieren" vs. "automatisch handeln" nach Risikoklasse.
- Explainability-Standard fuer alle high-impact suggestions.

### Exit-Kriterien

- Jede proaktive Empfehlung hat: Evidenz, Confidence, Risk Class, Feedback-Pfad.
- Regressionstests fuer Governance-Grenzen.

## Phase 5a - Live-UX & Zone Intelligence (parallel, 1-2 Wochen)

### Scope

- Hoher Informationsgehalt im 3-Tab Dashboard auf Basis realer Entitaeten (CO2, Laerm, Heizung, Medien, Energie).
- Konsolidierte Darstellung von Habitus-Zonen ohne Redundanz.

### Deliverables

- Hausverwaltung mit dynamischen Sektionen fuer `energy/heating/co2/noise/media/security/network/weather`.
- Graphische Verlaeufe fuer Energie und Luftqualitaet.
- Kompakte Zonenuebersicht mit rollenbasierter Aggregation.
- Habitus-Tab um CO2/Laerm-Verlauf erweitert.

### Exit-Kriterien

- Dashboard erzeugt aus Live-Daten ohne harte Abhaengigkeit auf manuell gepflegte Entity-Listen.
- Mindestens eine verwertbare Verlaufsvisualisierung je Kategorie Energie + Luftqualitaet vorhanden.

---

## Statusupdate dieses Zyklus (2026-02-27)

Bereits umgesetzt:
- Core NeuronManager: Callback-Kompatibilitaet + normalisierte Mood-Confidence + proaktive Callback-Weiterleitung.
- HA Dashboard-Pipeline: Infrastruktur-Erkennung erweitert (`media`, `co2`, `noise`) und heuristisch verbessert.
- 3-Tab Dashboard: Habitus/Hausverwaltung mit mehr Live-Signal-Dichte (CO2, Laerm, Medien, Verlaeufe, Zonenuebersicht).
- Testanpassungen fuer neue Infrastrukturkategorien.
- Neues Gesamtkonzept: `docs/INTEGRATION_CONCEPT_v11.2_LIVE_HA.md`.

---

## Arbeitsmethoden (empfohlen)

1. **ADR + RFC leichtgewichtig**
- Jede relevante Architekturentscheidung kurz dokumentieren (Problem, Optionen, Entscheidung, Folgen).

2. **Strangler-Refactor statt Rewrite**
- Neue Registry/Factory/Lifecycle-Schichten einfuehren und Altpfade schrittweise ablösen.

3. **Contract-Tests als Gate**
- Producer/Consumer-Tests in beiden Repos als Pflicht vor Release.

4. **Release Train mit festen Gates**
- Version Sync, Contract Sync, Docs Sync, Critical Path Tests, Guard-Workflow.

5. **Evidence-first Statusberichte**
- Status nur aus messbaren Artefakten: Test-Collect, Test-Pass, API-Snapshot, Version-Dateien.

---

## 30-Tage-Plan (konkret)

## Woche 1

- Phase 0 komplett abschliessen.
- Dokumentdrift aufloesen (Vision/Index/Status/Release Notes).
- CI-Job fuer Docs-Freshness aktivieren.

## Woche 2

- Kritische Contract-Schemas definieren.
- Ersten End-to-End Contract-Testpfad in beiden Repos aktiv schalten.

## Woche 3

- Core Boot-Unification beginnen (gemeinsamer Factory-Kern).
- Registry-basierte Blueprint-Liste als interne Wahrheit einfuehren.

## Woche 4

- HA Runtime-Profile implementieren (minimal/standard/full).
- Erste Module auf Manifest-/Prerequisite-Logik umstellen.

---

## Release-Gates (ab sofort)

Ein Release ist nur "ready", wenn alle Punkte gruen sind:

- Version Sync: HA/Core/Runtime-Dateien identisch
- Contract Sync: keine unversionierten API-Aenderungen
- Docs Sync: Baseline in Kern-Dokumenten aktuell
- Tests: Critical path + collect-only plausibel
- Guard Workflows: erfolgreich in beiden Repos

---

## Messbare Erfolgskennzahlen

- Dokumentdrift: 0 zentrale Dateien mit alter Baseline
- Contract-Verletzungen in CI: 0
- Anteil refaktorisierter Monolith-Bereiche: >60% bis v12.0
- Startup Stabilitaet bei Modulfehlern: keine globalen Setup-Abbrueche
- Governance-Treue: 100% high-risk Vorschlaege mit expliziter Nutzerentscheidung

---

Siehe `VISION.md` fuer Mission und Leitprinzipien. Dieses Dokument ist der operative Umsetzungsplan.
