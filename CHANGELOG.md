# Changelog - PilotSuite Core Add-on

## [0.9.1-alpha.5] - 2026-02-17

### Fixed
- **Race Conditions Fix:** asyncio.Lock für Event Forwarder Queue (forwarder_n3.py)
  - _queue_lock initialisiert
  - _enqueue_event() mit async with self._queue_lock
  - _flush_events() mit async with self._queue_lock

### Added
- **SQLite WAL Mode:** Brain Graph Store mit WAL Mode aktiviert
  - PRAGMA journal_mode=WAL für bessere Concurrency
  - PRAGMA synchronous=NORMAL für Safety/Performance Balance

### Tests
- Syntax-Check: ✅ forwarder_n3.py, store.py kompilieren
- Thread-Safety: ✅ asyncio.Lock implementiert
- WAL Mode: ✅ SQLite Concurrency optimiert

---

## [0.9.1-alpha.4] - 2026-02-17