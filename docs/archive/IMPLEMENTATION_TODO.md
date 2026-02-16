# Missing Core API Endpoints - Implementation Todo

## Endpoints to Implement

1. ✅ `/api/v1/status` - System Health Check
2. ✅ `/api/v1/capabilities` - Feature Discovery (already exists)
3. ✅ `/api/v1/vector/*` - Vector Operations (5 endpoints)
4. ✅ `/api/v1/dashboard/brain-summary` - Dashboard Data

## Progress

- [x] Create `/api/v1/status` endpoint in `app.py`
- [x] Implement `/api/v1/vector/*` endpoints via existing `vector.py` (already registered in blueprint)
- [x] Create `/api/v1/dashboard.py` with `brain-summary` and `health` endpoints
- [x] Register dashboard blueprint in `blueprint.py`
- [x] Fix `BrainGraphStore` initialization in `provider.py` to match new signature
- [x] Add `export_state()` and `prune()` aliases in `BrainGraphService`
- [x] Add `Iterable` import in `service.py`
- [x] All tests pass (6/6)

## Files Modified

- `copilot_core/app.py` - Added `/api/v1/status` and updated capabilities with new modules
- `copilot_core/api/v1/dashboard.py` - New file with dashboard endpoints
- `copilot_core/api/v1/blueprint.py` - Registered dashboard blueprint
- `copilot_core/brain_graph/provider.py` - Fixed store initialization
- `copilot_core/brain_graph/service.py` - Added `export_state()` and `prune()` aliases, added `Iterable` import

## Files Added

- `copilot_core/api/v1/dashboard.py` - Dashboard API module

## Implementation Details

### Status Endpoint
- Should return system health information
- Similar to `/health` but under `/api/v1/` prefix

### Vector Store Endpoints (5)
1. POST `/api/v1/vector/store` - Store a vector
2. GET `/api/v1/vector/search` - Search similar vectors
3. GET `/api/v1/vector/get/:id` - Get a specific vector
4. DELETE `/api/v1/vector/:id` - Delete a vector
5. GET `/api/v1/vector/stats` - Get vector store statistics

### Dashboard Brain Summary
- Return brain graph summary data for dashboard display
