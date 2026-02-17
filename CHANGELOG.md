# CHANGELOG - PilotSuite HA Integration

## [0.14.1-alpha.5] - 2026-02-17

### Fixed
- **Race Conditions Fix:** asyncio.Lock für Event Forwarder Queue
  - _queue_lock initialisiert
  - _enqueue_event() mit async with self._queue_lock
  - _flush_events() mit async with self._queue_lock
  - Thread-safe Queue Operationen verhindern Race Conditions

### Tests
- Syntax-Check: ✅ forwarder_n3.py kompiliert
- Thread-Safety: ✅ asyncio.Lock implemented

---

## [0.14.1-alpha.4] - 2026-02-17