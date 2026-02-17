# Changelog - PilotSuite Core Add-on

## [0.9.1-alpha.4] - 2026-02-17

### Fixed
- **Port-Konflikt:** HA Add-on Standard Port 8099 (nicht 8909!)
  - config.json: ingress_port=8099, ports 8099/tcp:8099
  - main.py: PORT default 8099
  - README.md, VISION.md: Alle Port-Referenzen auf 8099
  - HACS Integration: Port auf 8099 korrigiert

### Tests
- Syntax-Check: ✅ Alle Python-Dateien kompilieren ohne Fehler
- Port-Konfiguration: ✅ HA Add-on mit Port 8099 konfigurierbar

---

## [0.9.1-alpha.3] - 2026-02-17

### Fixed
- **Port-Konflikt:** Alle Port-Referenzen von 8099 → 8909 korrigiert
  - `config.json`: ingress_port und webui URL auf 8909
  - `README.md`: Alle Port-Referenzen auf 8909
  - `VISION.md`: Core Add-on Port auf 8909

### Documentation
- Alle Port-Referenzen konsistent auf 8909 aktualisiert

### Tests
- Syntax-Check: ✅ Alle Python-Dateien kompilieren ohne Fehler
- Konfiguration: ✅ config.json valid (ingress_port=8909)

---

## [0.9.1-alpha.2] - 2026-02-17

### Fixed
- **Port-Konflikt:** Alle Port-Referenzen von 8099 → 8909 korrigiert
  - `config.json`: ingress_port und webui URL auf 8909
  - `README.md`: Alle Port-Referenzen auf 8909
  - `VISION.md`: Core Add-on Port auf 8909

### Documentation
- Alle Port-Referenzen konsistent auf 8909 aktualisiert

### Tests
- Syntax-Check: ✅ Alle Python-Dateien kompilieren ohne Fehler
- Konfiguration: ✅ config.json valid (ingress_port=8909)

---

## [0.9.1-alpha.1] - 2026-02-17