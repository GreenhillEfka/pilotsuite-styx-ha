# AI Home CoPilot Architecture Review
**Date:** 2026-02-16 05:30 (Europe/Berlin)  
**Reviewer:** Gemini Architect Worker  
**Scope:** HA Integration v0.13.3 + Core Add-on v0.8.4

---

## Executive Summary

**Overall Score: 7/10** ⭐⭐⭐⭐⭐⭐⭐

The AI Home CoPilot project demonstrates solid architecture fundamentals with well-structured modules, comprehensive test coverage (346 tests passing), and clear separation of concerns. However, critical integration gaps exist between the Zone System and core components, creating a "zone-blind" state that limits context-aware functionality.

**Key Strengths:**
- Clean repository state (both synced, no pending changes)
- Comprehensive HabitusZoneV2 system with state machine and conflict resolution
- Performance infrastructure (QueryCache, ConnectionPool) production-ready
- Well-documented architecture decisions in HEARTBEAT.md

**Critical Gaps:**
- Zone Registry Integration incomplete (forwarder uses area names, not zone IDs)
- Media Context has placeholder zone integration
- No shared SDK between HA Integration and Core Add-on (drift risk)

---

## Architecture Assessment

### Component Overview

| Component | Files | Lines | Tests | Status |
|-----------|-------|-------|-------|--------|
| HA Integration | 117 | 9,413 | 346/0/0/2 ✅ | Production Ready |
| Core Add-on | 133 | 25,114 | 25+ ✅ | Production Ready |
| HabitusZoneV2 | 1 | ~500 | Dedicated | Implemented ✅ |
| Brain Graph | Multiple | ~1,200 | Covered | Implemented ✅ |

### Test Coverage

```
HA Integration:
- 346 passed
- 0 failed  
- 2 skipped
- Duration: 1.55s

Core Add-on:
- 25+ tests passing
- Smoke tests validated
```

---

## Critical Issues

### 1. Zone Registry Integration Gap 🔴 CRITICAL

**Location:** `forwarder.py:285-311`

**Problem:**
```python
# Current implementation uses area.normalized_name
if entity.area_id:
    area = area_registry.async_get(entity.area_id)
    if area:
        zone_id = area.normalized_name  # ❌ NOT HabitusZoneV2 ID!
```

**Impact:** The entire zone event pipeline operates on "area names" (e.g., "Wohnbereich") instead of HabitusZoneV2 IDs (e.g., "zone:wohnbereich"). This creates:

1. **Semantic Disconnect:** Brain Graph receives area names, not zone metadata
2. **Conflict Resolution Bypassed:** ZoneConflictResolver never activated
3. **State Machine Unused:** Zone states (idle/active/transitioning) not tracked

**Evidence:**
- `media_context_v2.py:307` calls `_get_zone_name()` which returns `zone_id.capitalize()` as placeholder
- No integration with `HabitusZoneStoreV2` for zone metadata lookup

**Recommendation:** Implement Decision 7 (Zone Registry Integration) immediately.

---

### 2. Media Context Zone Placeholder 🟠 HIGH

**Location:** `media_context_v2.py:88-89, 307`

**Problem:**
```python
def _get_zone_name(name: str) -> str:
    """Normalize zone/area name for matching."""
    # Placeholder - no HabitusZoneV2 lookup
    return zone_id.capitalize()
```

**Impact:** Media suggestions lack zone context (priority, hierarchy, state), reducing suggestion quality.

---

### 3. API Authentication Drift Risk 🟡 MEDIUM

**Location:** HA Integration ↔ Core Add-on communication

**Observation:** No shared SDK or contract validation between components. API changes in Core Add-on may break HA Integration without detection.

**Evidence:**
- Core Add-on at `/addons/copilot_core/rootfs/usr/src/app/`
- HA Integration at `/custom_components/ai_home_copilot/`
- No shared types/interfaces module

---

## Technical Debt List

| ID | Location | Description | Priority | Effort |
|----|----------|-------------|----------|--------|
| TD-001 | forwarder.py:285-311 | Zone mapping uses area names not zone IDs | P1 | 50 lines |
| TD-002 | media_context_v2.py:307 | Placeholder zone integration | P1 | 30 lines |
| TD-003 | vector_client.py:570 | MUPL integration pending | P2 | 80 lines |
| TD-004 | Cross-repo | No shared SDK/types | P2 | ~200 lines |
| TD-005 | Core Add-on | No Prometheus metrics format | P3 | Optional |

---

## Recommendations

### Immediate (P1 - This Week)

1. **Implement Zone Registry Integration**
   ```python
   # forwarder.py - Enhanced _build_zone_map()
   from .habitus_zones_store_v2 import async_get_zones_v2
   
   async def _build_zone_map(self):
       zones = await async_get_zones_v2(self.hass)
       zone_by_area = {}
       
       for zone in zones.values():
           # Map area names to zone IDs
           normalized = zone.name.lower().replace(" ", "_")
           zone_by_area[normalized] = zone.zone_id
       
       # Now use zone.zone_id instead of area.normalized_name
   ```

2. **Fix Media Context Zone Lookup**
   ```python
   # media_context_v2.py
   async def _get_zone_metadata(self, zone_id: str) -> dict:
       zones = await async_get_zones_v2(self.hass)
       zone = zones.get(zone_id)
       return {
           "priority": zone.priority if zone else 0,
           "state": zone.current_state if zone else "idle",
           "hierarchy": zone.zone_type if zone else "room"
       }
   ```

### Short-term (P2 - Next Sprint)

3. **Create Shared SDK Module**
   - Location: `/config/.openclaw/workspace/ai_home_copilot_sdk/`
   - Contents: Types, interfaces, constants shared by both repos
   - Prevents API drift

4. **Add Contract Tests**
   - Verify HA Integration → Core Add-on API compatibility
   - Run in CI pipeline

### Long-term (P3 - Future)

5. **Prometheus Metrics Format**
   - Optional: Convert `/api/v1/performance/metrics` to Prometheus text format
   - Current JSON format works for internal monitoring

---

## Next Steps (Prioritized)

| Step | Action | Owner | Est. Time | Dependencies |
|------|--------|-------|-----------|--------------|
| 1 | Implement Zone Registry Integration (Decision 7) | Dev | 4h | None |
| 2 | Fix media_context_v2.py zone lookup | Dev | 2h | Step 1 |
| 3 | Add MUPL integration to vector_client | Dev | 4h | None |
| 4 | Create shared SDK proposal | Architect | 2h | None |
| 5 | Add API contract tests | Dev | 3h | Step 4 |

---

## Risk Assessment

**Current Risk Level: MEDIUM** 🟡

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Zone events misrouted | High | High | Fix TD-001 immediately |
| API drift between repos | Medium | Medium | Create shared SDK |
| Test coverage gaps | Low | Low | Add contract tests |

---

## Files Analyzed

### HA Integration (117 files)
- `custom_components/ai_home_copilot/forwarder.py` - Zone mapping issue
- `custom_components/ai_home_copilot/media_context_v2.py` - Zone placeholder
- `custom_components/ai_home_copilot/habitus_zones_store_v2.py` - Zone system ✅

### Core Add-on (133 files)
- `copilot_core/performance.py` - Production ready ✅
- `copilot_core/brain_graph/` - Well structured ✅
- `copilot_core/mupl/` - Privacy model implemented ✅

---

## Conclusion

The architecture is fundamentally sound with a 7/10 score. The primary blocker is the Zone Registry Integration gap (TD-001) which prevents the HabitusZoneV2 system from functioning as designed. This is a known issue documented in HEARTBEAT.md as Decision 7 (PROPOSED).

**Recommendation:** Prioritize implementing Decision 7 before adding new features. The zone system is foundational to context-aware suggestions and must be operational for the system to achieve its design goals.

---

*Generated by Gemini Architect Worker - 2026-02-16*