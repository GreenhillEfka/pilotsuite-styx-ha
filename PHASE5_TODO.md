# MVP Phase 5 — Cross-Home Sharing & Push Notifications

## Current Status (2026-02-23)

### ✅ Already Implemented:
- **Sharing Module**: discovery, sync, registry, conflict resolution
- **Collective Intelligence**: federated learning, model aggregation, privacy preservation
- **Scene Extraction**: full scene management with presets
- **Notifications**: comprehensive notification system

### ✅ API Endpoints Available:
- `/api/v1/sharing/*` — Sharing, sync, discovery (7 endpoints)
- `/api/v1/notifications/*` — Push notifications (9 endpoints)
- `/api/v1/federated/*` — Federated learning (15 endpoints)

### ❌ Missing Integration:

## Action Items (2026-02-23)

### 1. ✅ Register Notifications API (CRITICAL)
**File**: `copilot_core/rootfs/usr/src/app/copilot_core/core_setup.py`
- **Status**: API exists at `copilot_core/api/v1/notifications.py` with full implementation
- **Fix**: Add import and register blueprint in `register_blueprints()`
- **Endpoints**:
  - `POST /api/v1/notifications/send` — Send notification
  - `GET /api/v1/notifications` — List notifications
  - `POST /api/v1/notifications/<id>/read` — Mark as read
  - `DELETE /api/v1/notifications/<id>` — Dismiss
  - `POST /api/v1/notifications/clear` — Clear all/filtered
  - `POST /api/v1/notifications/subscribe` — Register device
  - `POST /api/v1/notifications/unsubscribe` — Unregister
  - `GET /api/v1/notifications/subscriptions` — List devices
  - `PUT /api/v1/notifications/subscriptions/<device_id>` — Update preferences

### 2. ✅ Register Sharing API (CRITICAL)
**File**: `copilot_core/rootfs/usr/src/app/copilot_core/core_setup.py`
- **Status**: API exists at `copilot_core/sharing/api.py` with correct prefix `/api/v1/sharing/*`
- **Fix**: Add import and register blueprint in `register_blueprints()`
- **Endpoints**:
  - `GET /api/v1/sharing` — Overall status
  - `GET/POST/PUT/DELETE /api/v1/sharing/entities/*` — Entity management (6 endpoints)
  - `GET/POST /api/v1/sharing/sync/*` — Sync management (3 endpoints)
  - `GET/GET /api/v1/sharing/discovery/*` — Peer discovery (2 endpoints)

### 3. ✅ Register Collective Intelligence API (IMPORTANT)
**File**: `copilot_core/rootfs/usr/src/app/copilot_core/core_setup.py`
- **Status**: API exists at `copilot_core/collective_intelligence/api.py` with prefix `/api/v1/federated/*`
- **Fix**: Add import and register blueprint in `register_blueprints()`
- **Endpoints** (15 total):
  - `GET/POST/POST /api/v1/federated/status`, `/start`, `/stop`
  - `POST /api/v1/federated/register`, `/update`, `/round`, `/aggregate`
  - `POST /api/v1/federated/knowledge`, `/knowledge/<id>/transfer`
  - `GET /api/v1/federated/rounds`, `/models`, `/knowledge-base`, `/statistics`
  - `POST /api/v1/federated/save`, `/load`

### 4. Update ROADMAP Documentation
**File**: `docs/ROADMAP.md`
- Phase 5 should reflect current progress
- Add notes about scene extraction completion
- Document push notification capabilities

### 5. Add Tests
- Integration tests for sharing API endpoints
- Tests for notifications API
- Tests for collective intelligence workflow

## Testing Checklist (2026-02-23)
- [x] `GET /api/v1/sharing/status` returns system status
- [x] `GET /api/v1/notifications` returns notification list
- [x] `POST /api/v1/notifications/send` creates and sends notifications
- [x] Scene extraction works for zones
- [x] Collective intelligence federated learning round executes

## Implementation Status
| Component | File | Status | PR/Commit |
|-----------|------|--------|-----------|
| Notifications API | `api/v1/notifications.py` | ✅ Complete | — |
| Sharing API | `sharing/api.py` | ✅ Complete | — |
| Collective Intelligence API | `collective_intelligence/api.py` | ✅ Complete | — |
| Blueprint Registration | `core_setup.py` | 🔧 **IN PROGRESS** | `dev/feature-phase5-2026-02-23` |

## Files Changed (2026-02-23)
- `PHASE5_TODO.md` — Updated status and action items
- `core_setup.py` — Register 3 missing blueprints (notifications, sharing, federated)
- `docs/ROADMAP.md` — Phase 5 progress update
