# AI Home CoPilot Architecture Review
**Date:** 2026-02-16 02:20
**Analyst:** Gemini Architect Worker
**Scope:** HA Integration + Core Add-on

---

## Executive Summary

### 🔴 Critical Findings (3)

1. **God Class Pattern Detected** - 5 files > 700 lines (config_flow.py: 1260, neurons/state.py: 764, brain_graph/service.py: 712, vector_store/store.py: 686, knowledge_graph/graph_store.py: 640)
   - **Risk:** HIGH - Maintenance burden, testing complexity, merge conflicts

2. **API Contract Drift** - Tag system has two implementations:
   - `tag_registry.py` (516 lines) in Integration
   - `tags/api.py` (544 lines) in Core
   - **Risk:** MEDIUM - Potential sync issues, duplicate logic

3. **Event Forwarding Complexity** - `forwarder_n3.py` (772 lines) handles 3+ event types with nested async patterns
   - **Risk:** MEDIUM - Error propagation, retry logic gaps

### 🟢 Positive Patterns

- **Test Coverage:** 346 tests passing (Integration)
- **Security:** P0 implemented (ast.parse() vs exec(), SHA256 validation)
- **Module Organization:** Clear separation (neurons/, brain_graph/, tags/)

---

## Detailed Analysis

### 1. God Class Detection

| File | Lines | Concern | Recommendation |
|------|-------|---------|----------------|
| config_flow.py | 1260 | Setup wizard with multiple flows | Split into: ConfigFlowBase, ZoneConfigFlow, UserConfigFlow |
| neurons/state.py | 764 | State management for all neurons | Extract per-neuron state handlers |
| brain_graph/service.py | 712 | Graph operations monolith | Split into: GraphBuilder, GraphQuery, GraphSync |
| vector_store/store.py | 686 | Vector operations + storage | Separate VectorOperations from VectorStorage |
| knowledge_graph/graph_store.py | 640 | KG persistence + queries | Extract KGQueries, KGWriter |

**Pattern:** Files > 500 lines indicate missing abstractions

### 2. API Consistency Check

#### Tag System Analysis

**Integration (tag_registry.py):**
- Local tag caching
- Entity tag assignment UI
- Tag validation

**Core (tags/api.py):**
- REST API endpoints
- Tag persistence
- Tag search

**Gap:**
- No clear API contract documented
- Potential for tag state drift between Integration cache and Core store
- Missing sync mechanism validation

#### Brain Graph Sync

**Files:**
- `brain_graph_panel.py` (947 lines) - Integration UI
- `brain_graph/service.py` (712 lines) - Core logic
- `brain_graph/bridge.py` (539 lines) - HA bridge
- `brain_graph_sync.py` (541 lines) - Sync logic

**Concern:** 4 files, 2839 total lines handling brain graph
- **Recommendation:** Consolidate into clear layers:
  - UI Layer: brain_graph_panel.py
  - API Layer: brain_graph/api.py
  - Sync Layer: bridge.py
  - Remove: brain_graph_sync.py (merge into bridge)

### 3. Event Forwarding Architecture

**forwarder_n3.py (772 lines) handles:**
- State change events
- Service call events
- Zone context events
- Retry logic
- Error tracking

**Technical Debt:**
- Mixed concerns (forwarding + retry + error handling)
- Deep nesting (3+ levels of async callbacks)
- No circuit breaker pattern

**Recommendation:**
```
forwarder/
├── base.py        # AbstractForwarder
├── state.py       # StateChangeForwarder
├── service.py     # ServiceCallForwarder
├── retry.py       # RetryPolicy (extracted)
└── circuit.py     # CircuitBreaker (add)
```

### 4. Module Connector Pattern

**module_connector.py (639 lines)**

**Current Responsibilities:**
- WebSocket connection management
- Heartbeat handling
- Reconnection logic
- Error state management
- API client delegation

**Issues:**
- Single point of failure
- No connection pooling
- Synchronous init in async context

**Recommendation:**
```
connector/
├── client.py      # APIClient
├── websocket.py   # WebSocketManager
├── retry.py       # RetryStrategy
└── health.py      # HealthChecker
```

### 5. Test Coverage Analysis

**HA Integration:** 346 passed, 0 failed, 2 skipped ✅
**Core Add-on:** 582 tests collected ✅ (discovered during this review)

**Gaps Identified:**
- Integration tests for module_connector missing
- Edge cases in forwarder_n3 not covered
- 1 PytestCollectionWarning in test_e2e_pipeline.py

**Recommendation:**
- Add Core Add-on test metrics to HEARTBEAT.md
- Target: 80% coverage for files > 500 lines

---

## Technical Debt Inventory

### High Priority (P0)

| ID | Item | Effort | Risk |
|----|------|--------|------|
| TD-01 | config_flow.py refactoring | 3 days | HIGH |
| TD-02 | Tag system API contract | 2 days | MEDIUM |
| TD-03 | forwarder_n3 async patterns | 2 days | MEDIUM |

### Medium Priority (P1)

| ID | Item | Effort | Risk |
|----|------|--------|------|
| TD-04 | neurons/state.py extraction | 2 days | MEDIUM |
| TD-05 | brain_graph consolidation | 3 days | LOW |
| TD-06 | module_connector split | 2 days | LOW |

### Low Priority (P2)

| ID | Item | Effort | Risk |
|----|------|--------|------|
| TD-07 | vector_store refactoring | 2 days | LOW |
| TD-08 | knowledge_graph extraction | 1 day | LOW |
| TD-09 | Core test metrics | 1 day | LOW |

---

## Architecture Improvement Recommendations

### 1. Introduce Layered Architecture

```
┌─────────────────────────────────────────────┐
│  Presentation Layer (UI/Dashboard Cards)    │
├─────────────────────────────────────────────┤
│  Integration Layer (HA Bridge)             │
├─────────────────────────────────────────────┤
│  Service Layer (Core APIs)                 │
├─────────────────────────────────────────────┤
│  Domain Layer (Neurons/Synapses)          │
├─────────────────────────────────────────────┤
│  Infrastructure Layer (Storage/Vector)     │
└─────────────────────────────────────────────┘
```

### 2. API Versioning

**Current:** No versioning
**Recommendation:** `/api/v1/`, `/api/v2/` paths
- v1: Stable, backward-compatible
- v2: Experimental features (user_hints, mood_v2)

### 3. Error Handling Standardization

**Current:** Mixed (try/except scattered, error_tracking.py)
**Recommendation:**
- Centralized ErrorHandler middleware
- Structured error codes (E1xxx Integration, E2xxx Core)
- Error catalog in docs/

### 4. Documentation Debt

**Missing:**
- API contract between Integration ↔ Core
- Architecture decision records (ADRs)
- Onboarding guide for contributors

**Recommendation:** Create `docs/architecture/` with:
- API_CONTRACTS.md
- ADRs/ (numbered decisions)
- CONTRIBUTING.md

---

## Action Items (Priority Ranked)

### Immediate (This Week)

1. ✅ Commit pending test fixes (already done per HEARTBEAT.md)
2. 📝 Define Tag API contract in docs/
3. 📊 Add Core Add-on test metrics to HEARTBEAT.md

### Short-term (2 Weeks)

4. 🔧 Extract retry logic from forwarder_n3.py
5. 📖 Create ADR for brain_graph sync strategy
6. 🧪 Add integration tests for module_connector

### Medium-term (1 Month)

7. ♻️ Refactor config_flow.py into focused flows
8. 🏗️ Introduce layered architecture enforcement
9. 📚 Create contributor onboarding docs

---

## Risk Assessment

| Area | Current Risk | Mitigation | Target Risk |
|------|--------------|------------|-------------|
| God Classes | HIGH | Refactor P0 items | MEDIUM |
| API Drift | MEDIUM | Contract docs | LOW |
| Test Coverage | MEDIUM | Add Core metrics | LOW |
| Documentation | HIGH | Create docs/ | MEDIUM |

---

## Conclusion

The AI Home CoPilot architecture is functional with strong test coverage (346 tests). Primary concerns are:

1. **5 God classes** requiring extraction
2. **Tag system duplication** needing API contract
3. **Event forwarding complexity** benefiting from decomposition

**Estimated remediation effort:** 15 developer-days for P0/P1 items

**Next review:** After P0 items resolved (~2 weeks)
