# HEARTBEAT.md

## AI Home CoPilot: Decision Matrix Status

**Status:** Phase 5 Complete ✅ (Updated 2026-02-16 02:50)

### Test Results (2026-02-16 06:05):
- **HA Integration**: 346 passed, 0 failed, 2 skipped ✅
- **Core Add-on**: 528 passed, 0 failed ✅

### Repo Status (Verified):
| Repo | Version | Git Status | Tests | Sync |
|------|---------|------------|-------|------|
| HA Integration | v0.13.3 | Clean | 346/0/0/2 ✅ | origin/main ✅ |
| Core Add-on | v0.8.4 | Clean | 528 ✅ | origin/main ✅ |

### Completed Features (v0.13.2):
- **Zone System v2**: 6 zones with conflict resolution
- **Zone Conflict Resolution**: 5 strategies (HIERARCHY, PRIORITY, USER_PROMPT, MERGE, FIRST_WINS)
- **Zone State Persistence**: HA Storage API, state machine (idle/active/transitioning/disabled/error)
- **Brain Graph Panel**: v0.8 with React frontend
- **Cross-Home Sync**: v0.2 multi-home coordination
- **Collective Intelligence**: v0.2 shared learning
- **SystemHealth API**: Core add-on health endpoints
- **Character System v0.1**: 5 presets
- **User Hints System**: Natural language → automation
- **P0 Security**: exec() → ast.parse(), SHA256, validation

### Next Milestones:
1. Performance optimization (caching, connection pooling)
2. Extended neuron modules (UniFi, Energy, Weather)
3. Multi-User Preference Learning (MUP) refinement

---

## Decision Matrix - Architecture Decisions (2026-02-16 03:54)

### Decision 1: Caching Strategy ✅ IMPLEMENTED
**Context:** Brain Graph queries have repeated lookups for same nodes
**Decision:** In-memory LRU cache, no Redis (local-first principle preserved)
- **Cache Size:** 1000 entries (configurable)
- **TTL:** 300 seconds (5 min)
- **Eviction:** LRU with TTL expiration
- **Implementation:** `copilot_core/performance.py` - QueryCache class ✅
- **Status:** Production-ready, stats exposed via `/api/v1/performance/stats`

### Decision 2: Connection Pooling ✅ IMPLEMENTED
**Context:** Core API creates new connections per request
**Decision:** SQLiteConnectionPool with bounded size
- **Pool Size:** Configurable, default 5 connections
- **Cleanup:** Idle connection cleanup available via `/api/v1/performance/pool/cleanup`
- **Implementation:** `copilot_core/performance.py` - ConnectionPool, SQLiteConnectionPool ✅
- **Status:** Production-ready, stats exposed via `/api/v1/performance/pool/status`

### Decision 3: Performance Metrics ✅ IMPLEMENTED
**Context:** Need visibility into system performance
**Decision:** Internal metrics API with cache/pool stats
- **Endpoint:** `/api/v1/performance/metrics` ✅
- **Metrics:** query_latency, cache_hit_rate, connection_pool_usage, event_throughput
- **Additional Endpoints:** `/api/v1/performance/stats`, `/api/v1/performance/cache/clear`
- **Implementation:** `copilot_core/performance.py` + `copilot_core/api/performance.py` ✅
- **Note:** Prometheus-compatible format NOT implemented (internal JSON only)
- **Status:** Production-ready for internal monitoring

### Decision 4: Neuron Module Refinement ✅
**Context:** 14 neurons implemented, need refinement for production
**Decision:** Staged rollout with A/B testing
- **Phase 1:** Presence, Activity, Time neurons (mature)
- **Phase 2:** Environment, Calendar, Cognitive neurons (needs real-world testing)
- **Phase 3:** Energy, Media neurons (dependent on HA entities)
- **Confidence Threshold:** 95% for auto-suggestions, 80% for learning

### Decision 5: MUPL Privacy Model ✅
**Context:** Multi-user preference learning needs clear privacy boundaries
**Decision:** Opt-in by default, differential privacy for federated learning
- **Privacy Mode:** `opt-in` (default) - users must consent
- **Differential Privacy:** ε=0.1 (high privacy, moderate utility)
- **Retention:** 90 days (configurable)
- **Min Interactions:** 5 before preference is considered stable

---

### Open TODOs (Prioritized):

**P1 - Zone Integration (High Impact):**
1. `forwarder.py:285-311`: Zone mapping from HA area/device registry
   - Status: Partial implementation exists (lines 285-311)
   - Uses `entity.area_id` and `device.area_id` to map to zones
   - TODO marker suggests full integration needed with HabitusZones v2
   - Impact: Better zone-based context for events

2. `media_context_v2.py:307`: Integration with habitus_zones_v2
   - `_get_zone_name()` returns `zone_id.capitalize()` as placeholder
   - Need to query HabitusZoneStoreV2 for zone metadata
   - Impact: Media context aware of zone semantics

**P2 - MUPL Integration:**
3. `vector_client.py:570`: Integrate with MUPL module for preferences
   - Currently returns similarity-based hints
   - Need to connect to MultiUserPreferenceLearning module
   - Impact: Personalized recommendations

**P3 - Prometheus Format (Optional):**
4. Performance metrics use internal JSON format
   - `/api/v1/performance/metrics` returns structured stats
   - Prometheus text format NOT implemented
   - Low priority - internal monitoring works

### Risk Assessment: LOW
- All repos clean and synced
- Tests passing (346/0/0/2)
- No breaking changes pending
- Next release: v0.13.3 (performance focus)

### Decision 6: Performance Module Architecture ✅ VERIFIED (2026-02-16 03:54)
**Context:** Review of existing performance infrastructure
**Decision:** Current implementation is production-ready
- **QueryCache:** LRU with TTL, 1000 entry default, thread-safe (OrderedDict + RLock)
- **SQLiteConnectionPool:** Bounded pool with idle cleanup
- **API Endpoints:** `/api/v1/performance/*` (stats, cache, pool, metrics)
- **PerformanceMonitor:** Records timing for operations
- **AsyncExecutor:** ThreadPoolExecutor for non-blocking I/O
- **Location:** `copilot_core/performance.py` (618 lines)
- **No Action Required:** Architecture decisions 1-3 already implemented

### Decision 7: Zone Registry Integration 📋 PROPOSED (2026-02-16 04:54)
**Context:** `forwarder.py:285-311` builds zone_map from HA area registry but uses `area.normalized_name` directly
**Issue:** No connection to HabitusZoneV2 system - entities mapped to "area names" not "zone IDs"
**Decision Proposal:** Two-phase integration

**Phase 1: Forwarder Zone Mapping Enhancement**
- Query HabitusZoneStoreV2 during `_build_zone_map()`
- Match HA areas to HabitusZoneV2 by:
  1. Exact match: `area.normalized_name == zone.zone_id.replace("zone:", "")`
  2. Fuzzy match: `area.name.lower() == zone.name.lower()`
  3. Fallback: Create implicit zone from area if no match
- Cache mapping in `_zone_map` with zone metadata (priority, hierarchy)

**Phase 2: Media Context Zone Integration**
- `media_context_v2.py:307` should call `async_get_zones_v2()` when `use_habitus_zones=True`
- Replace `_get_zone_name()` placeholder with lookup from HabitusZoneStoreV2
- Return zone.display_name instead of zone_id.capitalize()

**Implementation Priority:** P1 (high impact on context-aware suggestions)
**Estimated Effort:** ~50 lines changed, backward compatible
**Risk:** LOW - additive change, existing mapping still works as fallback

### Heartbeat Check (2026-02-16 05:38 - Claude Orchestrator):
1. HA Integration: v0.13.3 RELEASED ✅
2. Core Add-on: v0.8.4 RELEASED ✅
3. Both repos synced with origin ✅
4. GitHub releases created ✅
5. Tests: 346 passed, 2 skipped ✅

### Actions Taken (2026-02-16 05:38):
- Fixed version mismatch: manifest.json (0.13.2→0.13.3), config.json (0.8.1→0.8.4)
- Pushed commits to origin/main
- Created tags v0.13.3, v0.8.4
- Created GitHub releases with release notes

### Gemini Architect Review (2026-02-16 05:16):
**CRITICAL FINDING:** Zone Logic P1 upgraded to CRITICAL - system is "zone-blind"
- `forwarder.py` uses `area.normalized_name` not `HabitusZoneV2` IDs
- `media_context_v2.py` has placeholder zone integration
- Recommendation: Implement Zone Registry (Decision 7) immediately

**Security:** Audit API authentication between HA and Core Add-on

**Architecture:** Consider monorepo or shared SDK to prevent integration drift

**Full Report:** `notes/gemini_reports/2026-02-16_architecture_review.md`
