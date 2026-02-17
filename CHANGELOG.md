# CHANGELOG - PilotSuite HA Integration

## [0.14.1-alpha.4] - 2026-02-17

### Fixed
- **Port-Konflikt:** HA Add-on Standard Port 8099 (nicht 8909!)
  - const.py: DEFAULT_PORT=8099
  - forwarder_n3.py: core_url Fallback localhost:8099
  - services_setup.py: core_url Fallback localhost:8099
  - README.md: Alle Port-Referenzen auf 8099

### Tests
- Syntax-Check: ✅ const.py, forwarder_n3.py, services_setup.py kompilieren
- Port-Konfiguration: ✅ HACS Integration mit Port 8099 konfigurierbar

---

## [0.14.1-alpha.3] - 2026-02-17