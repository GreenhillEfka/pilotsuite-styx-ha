# PilotSuite HACS Integration -- Entwickler- und Contributing-Guide

> Dieses Dokument richtet sich an Entwickler, die an der PilotSuite HACS Integration mitarbeiten moechten. Es beschreibt Umgebung, CI, Tests, Architektur-Patterns und haeufige Stolperfallen.

---

## 1. Entwicklungsumgebung

### Voraussetzungen

- **Python 3.11+** (die CI testet gegen 3.11)
- **Home Assistant Development Environment** -- entweder ein laufendes HA-Dev-Setup oder `homeassistant` als pip-Abhaengigkeit fuer Type Checking
- **pytest**, **pytest-asyncio**, **pytest-cov** fuer Tests
- **bandit** fuer Security-Scans (optional lokal)

### Setup

```bash
# Repo klonen
git clone https://github.com/<org>/pilotsuite-styx-ha.git
cd pilotsuite-styx-ha

# Virtuelle Umgebung erstellen
python3.11 -m venv venv
source venv/bin/activate

# Test-Abhaengigkeiten installieren
pip install pytest pytest-asyncio pytest-cov

# Optional: Security-Scanner
pip install bandit
```

### Verzeichnisstruktur

```
pilotsuite-styx-ha/
+-- custom_components/ai_home_copilot/
|   +-- __init__.py              # Integration Setup
|   +-- coordinator.py           # DataUpdateCoordinator + API Client
|   +-- entity.py                # CopilotBaseEntity Basisklasse
|   +-- const.py                 # Konstanten, DOMAIN, Config Keys
|   +-- config_flow.py           # Config + Options Flow
|   +-- core/
|   |   +-- runtime.py           # CopilotRuntime -- Modul-Lifecycle
|   |   +-- module.py            # CopilotModule Protocol
|   |   +-- registry.py          # ModuleRegistry
|   +-- sensors/                 # Sensor-Entities
|   +-- translations/            # en.json, de.json
|   +-- strings.json             # Config-Flow-Strings (Quelle der Wahrheit)
|   +-- manifest.json            # HA Manifest
+-- tests/                       # pytest Test-Suite
+-- pytest.ini                   # pytest-Konfiguration
+-- .github/workflows/ci.yml     # CI Pipeline
+-- hacs.json                    # HACS Metadaten
```

---

## 2. CI Pipeline

Die CI (``.github/workflows/ci.yml``) laeuft bei jedem Push und Pull Request. Sie besteht aus **5 Jobs**, die alle bestanden werden muessen, bevor ein Release gueltig ist:

| Job | Tool | Beschreibung |
|-----|------|--------------|
| **lint** | `py_compile` | Syntax-Check aller Python-Dateien + JSON-Validierung von `strings.json` und `translations/en.json` |
| **pytest** | `pytest` | Vollstaendige Test-Suite mit Coverage-Report (haengt von lint ab) |
| **security** | `bandit` | Security-Scan, Schweregrad Low+Low, ueberspringt B101/B404/B603 |
| **hacs** | `hacs/action@main` | HACS-Validierung (Struktur, manifest.json, hacs.json) |
| **hassfest** | `home-assistant/actions/hassfest@master` | Home-Assistant-Validierung (manifest, strings, services, config_flow Konsistenz) |

### Abhaengigkeiten zwischen Jobs

```
lint --> pytest
lint --> security
lint --> hacs --> hassfest
```

**Wichtig:** hassfest validiert, dass `strings.json` exakt zur Struktur des ConfigFlow passt. Wenn der ConfigFlow Menues verwendet (`async_show_menu`), muessen in `strings.json` die `menu_options` definiert sein -- nicht `data`. Umgekehrt brauchen Formulare (`async_show_form`) einen `data`-Block. Jede Abweichung laesst hassfest fehlschlagen.

---

## 3. Tests

### Konfiguration

Die Datei `pytest.ini` definiert:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
pythonpath = .
markers =
    unit: Unit tests ohne HA-Abhaengigkeit
    integration: Integration tests mit HA-Framework
    asyncio: mark test as async
```

### Tests ausfuehren

```bash
# Vollstaendige Suite mit Verbose-Output
python -m pytest tests/ -v

# Mit Coverage
python -m pytest tests/ -v --tb=short \
  --cov=custom_components/ai_home_copilot \
  --cov-report=term-missing

# Einzelne Testdatei
python -m pytest tests/test_forwarder_n3.py -v

# Nur Unit-Tests
python -m pytest tests/unit/ -v
```

### Test-Patterns

- **Unit-Tests** (`tests/unit/`): Keine HA-Abhaengigkeit, testen isolierte Logik
- **Integration-Tests** (`tests/integration/` und `tests/test_*.py`): Verwenden HA-Mocks, testen Zusammenspiel mit dem Framework
- Async-Tests funktionieren dank `asyncio_mode = auto` automatisch -- kein `@pytest.mark.asyncio` noetig
- Gemeinsame Fixtures liegen in `tests/conftest.py`

---

## 4. Neues Modul erstellen

Module implementieren das `CopilotModule`-Protocol aus `core/module.py`:

```python
@runtime_checkable
class CopilotModule(Protocol):
    @property
    def name(self) -> str: ...

    async def async_setup_entry(self, ctx: ModuleContext) -> None: ...

    async def async_unload_entry(self, ctx: ModuleContext) -> bool: ...
```

### Schritt-fuer-Schritt

1. **Modul-Klasse erstellen** -- z.B. `custom_components/ai_home_copilot/mein_modul.py`:

```python
from __future__ import annotations

import logging

from .core.module import CopilotModule, ModuleContext

_LOGGER = logging.getLogger(__name__)


class MeinModul:
    """Beispiel-Modul."""

    @property
    def name(self) -> str:
        return "mein_modul"

    async def async_setup_entry(self, ctx: ModuleContext) -> None:
        _LOGGER.info("MeinModul gestartet")
        # Initialisierung hier

    async def async_unload_entry(self, ctx: ModuleContext) -> bool:
        _LOGGER.info("MeinModul entladen")
        # Cleanup hier (Listener entfernen, Tasks abbrechen)
        return True
```

2. **Im Registry registrieren** -- In der Stelle, wo Module registriert werden (ueber `CopilotRuntime.registry.register()`):

```python
runtime = CopilotRuntime.get(hass)
runtime.registry.register("mein_modul", MeinModul)
```

3. **Sensoren hinzufuegen** -- Neue Datei in `sensors/` erstellen. Alle Sensor-Entities muessen von `CopilotBaseEntity` erben:

```python
from ..entity import CopilotBaseEntity

class MeinSensor(CopilotBaseEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "ai_home_copilot_mein_sensor"
        self._attr_name = "Mein Sensor"

    @property
    def native_value(self):
        return self.coordinator.data.get("mein_wert")
```

4. **unique_id-Konvention:** Immer mit `ai_home_copilot_` prefixen. IDs muessen global eindeutig sein.

5. **Tests schreiben** -- Mindestens ein Test in `tests/` fuer das neue Modul.

---

## 5. Config Flow aendern

Der Config Flow ist aufgeteilt in mehrere Dateien:

- `config_flow.py` -- Haupt-ConfigFlow-Klasse (duenn, delegiert)
- `config_helpers.py` -- Hilfsfunktionen, Konstanten
- `config_schema_builders.py` -- Schema-Builder
- `config_wizard_steps.py` -- Wizard-Schritte
- `config_options_flow.py` -- OptionsFlowHandler
- `config_zones_flow.py` -- Zonen-Management

### strings.json-Struktur muss zum ConfigFlow passen

Das ist die haeufigste Fehlerquelle. hassfest prueft, dass jeder Step in `config_flow.py` korrekt in `strings.json` abgebildet ist:

- **Menue-Steps** (`async_show_menu`) brauchen `menu_options`:
  ```json
  "user": {
    "title": "...",
    "description": "...",
    "menu_options": {
      "zero_config": "Zero Config",
      "quick_start": "Quick Start",
      "manual_setup": "Manual Setup"
    }
  }
  ```

- **Formular-Steps** (`async_show_form`) brauchen `data`:
  ```json
  "manual_setup": {
    "title": "...",
    "description": "...",
    "data": {
      "host": "Host",
      "port": "Port"
    }
  }
  ```

### Checkliste bei Aenderungen

1. Step in `config_flow.py` (oder Unter-Dateien) aendern
2. `strings.json` aktualisieren -- Struktur muss exakt zum Step-Typ passen
3. `translations/en.json` synchronisieren -- muss dieselbe Struktur haben
4. Lokal testen: `python -m py_compile custom_components/ai_home_copilot/config_flow.py`
5. JSON validieren: `python -c "import json; json.load(open('custom_components/ai_home_copilot/strings.json'))"`
6. hassfest laeuft in der CI und wird Abweichungen sofort melden

---

## 6. Release-Prozess

### Ablauf

1. **Feature-Branch erstellen** vom aktuellen `main`
2. **Entwickeln und testen** (lokal + CI)
3. **Pull Request** gegen `main` oeffnen
4. **CI muss komplett gruen sein** -- besonders hassfest, da fehlende strings.json-Eintraege den Release blockieren
5. **PR mergen** nach Review
6. **CHANGELOG.md aktualisieren** mit den Aenderungen des neuen Release
7. **GitHub Release erstellen** mit Tag `vX.Y.Z`

### Warum der GitHub Release wichtig ist

HACS erkennt neue Versionen ausschliesslich ueber GitHub Release Tags. Ohne einen Release mit Tag `vX.Y.Z` wird das Update nicht an Nutzer ausgeliefert, auch wenn der Code auf `main` liegt.

```bash
# Release erstellen (nach PR-Merge und git pull)
gh release create vX.Y.Z --title "vX.Y.Z" --notes "Release notes"
```

### Versionierung

- Semantic Versioning: `vMAJOR.MINOR.PATCH`
- Breaking Changes erhoehen MAJOR
- Neue Features erhoehen MINOR
- Bugfixes erhoehen PATCH

---

## 7. Code-Konventionen

### Domain

Die technische Domain ist und bleibt **`ai_home_copilot`**. Auch nach der Umbenennung zu PilotSuite aendert sich die Domain nicht, da bestehende Installationen sonst brechen wuerden.

### Entity-Basisklasse

Alle Entities muessen von `CopilotBaseEntity` (in `entity.py`) erben. Diese stellt sicher:

- Einheitliche `device_info` fuer das HA-Device-Registry
- Konsistente Coordinator-Anbindung via `CoordinatorEntity`

```python
from .entity import CopilotBaseEntity

class MeineEntity(CopilotBaseEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "ai_home_copilot_mein_feature"
```

### Sprache

- **Code-Bezeichner** (Variablen, Funktionen, Klassen): Englisch
- **Kommentare und Docstrings**: Deutsch erlaubt
- **Logging-Nachrichten**: Englisch bevorzugt (fuer universelle Lesbarkeit in Logs)

### Keine Cloud-Abhaengigkeiten

PilotSuite ist Privacy-first und Local-first. Kein Modul darf externe Cloud-Services voraussetzen. Alle Daten bleiben lokal.

### Sichere hass.data-Zugriffe

Immer `.get()`-Ketten verwenden statt direkter Key-Zugriffe:

```python
# Richtig:
runtime = hass.data.get(DOMAIN, {}).get(DATA_CORE, {}).get(DATA_RUNTIME)

# Oder mit setdefault (wie in CopilotRuntime.get):
hass.data.setdefault(DOMAIN, {})
core = hass.data[DOMAIN].setdefault(DATA_CORE, {})

# Falsch -- KeyError wenn nicht initialisiert:
runtime = hass.data[DOMAIN][DATA_CORE][DATA_RUNTIME]
```

---

## 8. Sicherheit

### Keine Secrets im Code

Tokens, Passwoerter und API-Keys gehoeren in die HA-Konfiguration (Config Flow), nie in den Quellcode.

### PII-Redaktion in Events

Beim Weiterleiten von Events (z.B. Events Forwarder) muessen personenbezogene Daten (PII) vor dem Versand reduziert werden. Entity-IDs koennen Klarnamen enthalten.

### Begrenzte Speicherung

Alle internen Puffer, Queues und Caches muessen Groessenlimits haben. Unbegrenztes Wachstum fuehrt zu Speicherproblemen auf eingebetteten Systemen.

### Numerische Konfiguration mit Grenzen

Alle numerischen Config-Parameter muessen `vol.Range` verwenden:

```python
vol.Optional("max_batch", default=50): vol.All(
    int, vol.Range(min=1, max=1000)
),
```

### _safe_int / _safe_float

Hilfsfunktionen fuer das sichere Parsen von Nutzereingaben mit oberer Grenze:

```python
def _safe_int(value, default=0, upper=10000):
    try:
        v = int(value)
        return min(v, upper)
    except (ValueError, TypeError):
        return default
```

---

## 9. Haeufige Fehler

### hassfest schlaegt fehl: strings.json passt nicht zum ConfigFlow

**Symptom:** hassfest meldet fehlende Keys oder falsche Struktur.

**Ursache:** Ein Step verwendet `async_show_menu`, aber `strings.json` hat `data` statt `menu_options` (oder umgekehrt).

**Loesung:** Sicherstellen, dass der Step-Typ (`menu_options` vs. `data`) in `strings.json` exakt zum Code passt. Danach `translations/en.json` synchronisieren.

### set.pop() entfernt beliebige Elemente

**Symptom:** Unvorhersehbares Verhalten bei Sets, die als Queue oder FIFO verwendet werden.

**Ursache:** `set.pop()` in Python entfernt ein **beliebiges** Element, nicht das aelteste. Sets sind ungeordnet.

**Loesung:** Fuer geordnete Entfernung `collections.deque` oder `list` verwenden. Fuer atomaren Reset die gesamte Menge ersetzen statt einzeln zu entleeren.

### async_track_time_interval: Listener-Unsub speichern

**Symptom:** Timer-Callbacks laufen nach dem Entladen des Moduls weiter, was zu Fehlern und Speicherlecks fuehrt.

**Ursache:** Der Rueckgabewert von `async_track_time_interval` (die Unsub-Funktion) wurde nicht gespeichert.

**Loesung:** Unsub-Funktion in einer Instanzvariable oder Liste speichern und in `async_unload_entry` aufrufen:

```python
async def async_setup_entry(self, ctx: ModuleContext) -> None:
    self._unsub = async_track_time_interval(
        ctx.hass, self._async_update, timedelta(seconds=30)
    )

async def async_unload_entry(self, ctx: ModuleContext) -> bool:
    if self._unsub:
        self._unsub()
    return True
```

### Unsicherer hass.data[DOMAIN]-Zugriff

**Symptom:** `KeyError` beim Zugriff auf `hass.data[DOMAIN]` waehrend des Setups oder nach einem fehlgeschlagenen Laden.

**Ursache:** Direkter Dict-Zugriff ohne vorherige Pruefung, ob der Key existiert.

**Loesung:** Immer `.get()` oder `.setdefault()` verwenden (siehe Abschnitt Code-Konventionen oben). Besonders in Modulen, die unabhaengig vom Hauptsetup geladen werden koennen.

---

## Kurzreferenz

| Aufgabe | Befehl / Ort |
|---------|-------------|
| Tests ausfuehren | `python -m pytest tests/ -v` |
| Coverage | `python -m pytest tests/ -v --cov=custom_components/ai_home_copilot` |
| Syntax-Check | `python -m py_compile <datei.py>` |
| JSON validieren | `python -c "import json; json.load(open('...'))"` |
| Security-Scan | `bandit -r custom_components/ai_home_copilot -ll` |
| Release erstellen | `gh release create vX.Y.Z` |
| Entity Basisklasse | `CopilotBaseEntity` in `entity.py` |
| Modul-Interface | `CopilotModule` in `core/module.py` |
| Modul registrieren | `CopilotRuntime.registry.register(name, Factory)` |
| Domain | `ai_home_copilot` (aendert sich nicht) |
| unique_id Prefix | `ai_home_copilot_` |
