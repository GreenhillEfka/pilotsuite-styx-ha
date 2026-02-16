# 🔬 ERWEITERTE ANALYSE - Kritische Module

**Date:** 2026-02-16  
**Reviewer:** Gemini Critical Code Reviewer  

---

## P0-5: Events API ohne Authentifizierung (Events Endpoint)

**File:** `ha-copilot-repo/addons/copilot_core/rootfs/usr/src/app/copilot_core/api/v1/events.py`

**Location:** `@bp.post("")` und `@bp.get("")`

**Problem:**
```python
@bp.post("")
def ingest_event():
    payload = request.get_json(silent=True) or {}
    # KEINE AUTH CHECK! Jeder kann Events injecten
```

Der Events-Endpoint ist NICHT mit `@require_token` geschützt! Das bedeutet:
1. Jeder im Netzwerk kann Events injecten
2. Keine Validierung der Payload-Größe
3. Keine Rate-Limiting

**Fix:**
```python
from copilot_core.api.security import require_token

@bp.post("")
@require_token
def ingest_event():
    payload = request.get_json(silent=True) or {}
    # ... validation logic

@bp.get("")
@require_token
def list_events():
    # ...
```

---

## P0-6: SQL Injection Risk in Brain Graph Store

**File:** `ha-copilot-repo/addons/copilot_core/rootfs/usr/src/app/copilot_core/brain_graph/store.py`

**Location:** Multiple query methods using string formatting

**Problem:**
```python
def get_nodes(self, kinds: Optional[List[NodeKind]] = None, ...):
    query = "SELECT * FROM nodes WHERE 1=1"
    if kinds:
        placeholders = ",".join("?" * len(kinds))
        query += f" AND kind IN ({placeholders})"  # OK - parameterized
```

Das sieht sicher aus, ABER:

```python
def get_neighborhood(self, center_node: str, ...):
    # ...
    cursor.execute(
        f"SELECT * FROM edges WHERE from_node IN ({placeholders})",
        list(current_layer)  # OK
    )
```

**Potentielles Risiko:** Wenn `center_node` von User-Input kommt ohne Validierung:

```python
# Angenommen center_node kommt von API
center_node = request.args.get("node")  # Keine Validierung!
# Wenn center_node = "'; DROP TABLE nodes; --" -> SQL Injection!
```

**Fix:**
```python
def _validate_node_id(node_id: str) -> str:
    """Validate node ID format to prevent SQL injection."""
    import re
    if not re.match(r'^[a-zA-Z0-9_\-\.:\[\]]+$', node_id):
        raise ValueError(f"Invalid node ID format: {node_id}")
    return node_id

def get_neighborhood(self, center_node: str, ...):
    center_node = _validate_node_id(center_node)  # VALIDATE!
    # ...
```

---

## P1-4: Collective Intelligence - Privacy Leakage Risk

**File:** `ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/collective_intelligence.py`

**Location:** `async_create_pattern()` method

**Problem:**
```python
def _apply_differential_privacy(self, weights: Dict[str, float]) -> Dict[str, float]:
    if not self.privacy_epsilon or self.privacy_epsilon <= 0:
        return weights  # KEINE PRIVACY WENN EPSILON <= 0!
    
    # Add Laplace noise
    scale = 1.0 / self.privacy_epsilon
    noisy_weights = {}
    for key, value in weights.items():
        noise = np.random.laplace(0, scale)
        noisy_weights[key] = value + noise
```

Probleme:
1. `privacy_epsilon <= 0` deaktiviert Privacy komplett
2. Keine Validierung des Wertebereichs
3. `metadata` wird OHNE Privacy-Behandlung übertragen

**Fix:**
```python
def __init__(self, ..., privacy_epsilon: float = 1.0, ...):
    # VALIDATE epsilon
    if privacy_epsilon <= 0:
        raise ValueError("privacy_epsilon must be > 0")
    if privacy_epsilon > 10:
        _LOGGER.warning("High privacy_epsilon (%s) reduces privacy protection", privacy_epsilon)
    self.privacy_epsilon = max(0.1, min(privacy_epsilon, 10.0))  # Clamp to valid range

async def async_create_pattern(
    self,
    model_id: str,
    pattern_type: str,
    category: str,
    weights: Dict[str, float],
    metadata: Dict[str, Any],  # DANGER!
    confidence: float,
) -> Optional[SharedPattern]:
    # SANITIZE metadata - remove any identifying information
    sanitized_metadata = self._sanitize_metadata(metadata)
    
    # ...

def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Remove potentially identifying information from metadata."""
    # Whitelist of allowed metadata keys
    ALLOWED_KEYS = {
        "pattern_type", "category", "confidence", "sample_count",
        "model_version", "time_window", "aggregation_method"
    }
    
    sanitized = {}
    for key, value in metadata.items():
        if key in ALLOWED_KEYS:
            # Validate value types
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list):
                # Only allow primitive types in lists
                sanitized[key] = [v for v in value if isinstance(v, (str, int, float, bool))]
    
    return sanitized
```

---

## P1-5: Media Context V2 - Memory Leak in Manual Overrides

**File:** `ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/media_context_v2.py`

**Location:** `_get_valid_manual_target()` and `_get_valid_manual_zone()`

**Problem:**
```python
def _get_valid_manual_target(self) -> str | None:
    if not self._manual_target_entity_id:
        return None
    if self._manual_target_expires and time.time() > self._manual_target_expires:
        return None  # LEAK: Value is checked but never cleared!
    return self._manual_target_entity_id
```

Die Overrides werden nie aufgeräumt - sie bleiben für immer im Memory, auch wenn abgelaufen.

**Fix:**
```python
def _get_valid_manual_target(self) -> str | None:
    """Get manual target if still valid (not expired). Auto-cleanup."""
    if not self._manual_target_entity_id:
        return None
    if self._manual_target_expires and time.time() > self._manual_target_expires:
        # Auto-cleanup expired values
        self._manual_target_entity_id = None
        self._manual_target_expires = None
        _LOGGER.debug("Cleared expired manual target override")
        return None
    return self._manual_target_entity_id

def _get_valid_manual_zone(self) -> str | None:
    """Get manual zone if still valid (not expired). Auto-cleanup."""
    if not self._manual_zone_id:
        return None
    if self._manual_zone_expires and time.time() > self._manual_zone_expires:
        # Auto-cleanup expired values
        self._manual_zone_id = None
        self._manual_zone_expires = None
        _LOGGER.debug("Cleared expired manual zone override")
        return None
    return self._manual_zone_id

async def async_cleanup_expired_overrides(self) -> int:
    """Periodic cleanup task for expired overrides."""
    cleaned = 0
    if self._get_valid_manual_target() is None and self._manual_target_entity_id is not None:
        self._manual_target_entity_id = None
        self._manual_target_expires = None
        cleaned += 1
    if self._get_valid_manual_zone() is None and self._manual_zone_id is not None:
        self._manual_zone_id = None
        self._manual_zone_expires = None
        cleaned += 1
    return cleaned
```

---

## P2-4: HabitPredictor - Unbounded Memory Growth

**File:** `ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/ml/patterns/habit_predictor.py`

**Location:** `observe()` and pattern storage

**Problem:**
```python
def observe(self, device_id: str, event_type: str, ...):
    # ...
    self._update_device_pattern(device_id, event_type, timestamp)
    
def _update_device_pattern(self, device_id: str, event_type: str, timestamp: float):
    self.device_patterns[device_id].append({
        "event_type": event_type,
        "timestamp": timestamp,
    })
    # Keep only recent events (30 days)
    cutoff = timestamp - (30 * 24 * 3600)
    self.device_patterns[device_id] = [
        p for p in self.device_patterns[device_id] if p["timestamp"] >= cutoff
    ]
```

Probleme:
1. `device_patterns` Dictionary wächst unendlich mit neuen Devices
2. `sequence_patterns` hat KEIN Cleanup
3. `mood_patterns` hat partielle Cleanup-Logik
4. `time_patterns` wächst unendlich

**Fix:**
```python
class HabitPredictor:
    # Add configuration
    MAX_DEVICES = 100
    MAX_SEQUENCES_PER_DEVICE = 1000
    MAX_PATTERNS_PER_DEVICE = 10000
    CLEANUP_INTERVAL = 3600  # 1 hour
    
    def __init__(self, ...):
        # ...
        self._last_cleanup = time.time()
    
    def observe(self, device_id: str, event_type: str, ...):
        # Periodic cleanup
        if time.time() - self._last_cleanup > self.CLEANUP_INTERVAL:
            self._periodic_cleanup()
        
        # Limit device count
        if device_id not in self.device_patterns and len(self.device_patterns) >= self.MAX_DEVICES:
            self._evict_least_used_device()
        
        # ... rest of observe
    
    def _periodic_cleanup(self):
        """Comprehensive periodic cleanup of all pattern stores."""
        cutoff = time.time() - (30 * 24 * 3600)  # 30 days
        cleaned = {"devices": 0, "sequences": 0, "time_patterns": 0, "mood_patterns": 0}
        
        # Clean device patterns
        for device_id in list(self.device_patterns.keys()):
            old_count = len(self.device_patterns[device_id])
            self.device_patterns[device_id] = [
                p for p in self.device_patterns[device_id] if p["timestamp"] >= cutoff
            ]
            if not self.device_patterns[device_id]:
                del self.device_patterns[device_id]
            else:
                cleaned["devices"] += old_count - len(self.device_patterns[device_id])
        
        # Clean sequence patterns
        for pattern_key in list(self.sequence_patterns.keys()):
            old_count = len(self.sequence_patterns[pattern_key])
            self.sequence_patterns[pattern_key] = [
                seq for seq in self.sequence_patterns[pattern_key]
                if self._sequence_timestamp(seq, cutoff) >= cutoff
            ][:self.MAX_SEQUENCES_PER_DEVICE]  # Also limit count
            if not self.sequence_patterns[pattern_key]:
                del self.sequence_patterns[pattern_key]
            else:
                cleaned["sequences"] += old_count - len(self.sequence_patterns[pattern_key])
        
        # Clean time patterns
        for pattern_key in list(self.time_patterns.keys()):
            for time_key in list(self.time_patterns[pattern_key].keys()):
                old_count = len(self.time_patterns[pattern_key][time_key])
                self.time_patterns[pattern_key][time_key] = [
                    t for t in self.time_patterns[pattern_key][time_key] if t >= cutoff
                ]
                if not self.time_patterns[pattern_key][time_key]:
                    del self.time_patterns[pattern_key][time_key]
            if not self.time_patterns[pattern_key]:
                del self.time_patterns[pattern_key]
        
        # Clean mood patterns (already has some cleanup)
        for pattern_key in list(self.mood_patterns.keys()):
            for mood in list(self.mood_patterns[pattern_key].keys()):
                old_count = len(self.mood_patterns[pattern_key][mood])
                self.mood_patterns[pattern_key][mood] = [
                    t for t in self.mood_patterns[pattern_key][mood] if t >= cutoff
                ]
                if not self.mood_patterns[pattern_key][mood]:
                    del self.mood_patterns[pattern_key][mood]
            if not self.mood_patterns[pattern_key]:
                del self.mood_patterns[pattern_key]
        
        self._last_cleanup = time.time()
        _LOGGER.debug("Pattern cleanup: %s", cleaned)
    
    def _evict_least_used_device(self):
        """Evict the device with least recent activity."""
        if not self.device_patterns:
            return
        
        # Find device with oldest last event
        oldest_device = None
        oldest_time = float('inf')
        
        for device_id, events in self.device_patterns.items():
            if events:
                last_event = max(e["timestamp"] for e in events)
                if last_event < oldest_time:
                    oldest_time = last_event
                    oldest_device = device_id
        
        if oldest_device:
            del self.device_patterns[oldest_device]
            # Also clean related patterns
            for key in list(self.time_patterns.keys()):
                if oldest_device in key:
                    del self.time_patterns[key]
            for key in list(self.sequence_patterns.keys()):
                if oldest_device in key:
                    del self.sequence_patterns[key]
            _LOGGER.debug("Evicted least-used device: %s", oldest_device)
```

---

## P2-5: Collective Intelligence Service - Missing Async Support

**File:** `ha-copilot-repo/addons/copilot_core/rootfs/usr/src/app/copilot_core/collective_intelligence/service.py`

**Location:** All methods

**Problem:**
```python
class CollectiveIntelligenceService:
    def register_node(self, node_id: str, max_epsilon: float = 1.0) -> bool:
        # SYNCHRONOUS - könnte I/O blocken
        
    def submit_local_update(self, node_id: str, weights: Dict[str, Any], ...):
        # SYNCHRONOUS - model aggregation könnte teuer sein
        
    def save_state(self, path: str) -> bool:
        # SYNCHRONOUS FILE I/O!
        with open(path, "w") as f:  # BLOCKT!
            json.dump(state, f, indent=2)
```

Der Service ist komplett synchron, obwohl er in einem async Flask-Kontext läuft.

**Fix:**
```python
import asyncio
import aiofiles
import json

class CollectiveIntelligenceService:
    async def register_node_async(self, node_id: str, max_epsilon: float = 1.0) -> bool:
        """Async version of register_node."""
        if not self.is_active:
            return False
        # Run in executor for CPU-bound work
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.register_node, node_id, max_epsilon)
    
    async def save_state_async(self, path: str) -> bool:
        """Async save to file."""
        try:
            state = {
                "is_active": self.is_active,
                "status": self._status.to_dict(),
                "rounds": [r.to_dict() for r in self.learner.rounds],
                "aggregated_models": {
                    k: v.to_dict() for k, v in self.aggregator.aggregated_models.items()
                },
                "knowledge_base": {
                    k: v.to_dict() for k, v in self.knowledge_transfer.knowledge_base.items()
                },
                "timestamp": time.time(),
            }
            async with aiofiles.open(path, "w") as f:
                await f.write(json.dumps(state, indent=2))
            return True
        except Exception as e:
            _LOGGER.error("Failed to save state: %s", e)
            return False
    
    async def load_state_async(self, path: str) -> bool:
        """Async load from file."""
        try:
            async with aiofiles.open(path, "r") as f:
                content = await f.read()
            state = json.loads(content)
            # ... parse state
            return True
        except Exception as e:
            _LOGGER.error("Failed to load state: %s", e)
            return False
```

---

## P3-3: Type Safety - Missing Validation in HabitPredictor

**File:** `ai_home_copilot_hacs_repo/custom_components/ai_home_copilot/ml/patterns/habit_predictor.py`

**Problem:**
```python
def observe(
    self,
    device_id: str,
    event_type: str,
    timestamp: Optional[float] = None,
    context: Dict[str, Any] = None,
) -> None:
    # KEINE VALIDATION von device_id, event_type, context
```

**Fix:**
```python
from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any, List
import re

@dataclass
class DeviceEvent:
    """Type-safe device event."""
    device_id: str
    event_type: Literal["on", "off", "state_change", "trigger"]
    timestamp: float
    context: Dict[str, Any]
    
    @classmethod
    def validate_device_id(cls, device_id: str) -> str:
        """Validate device ID format."""
        if not device_id:
            raise ValueError("device_id cannot be empty")
        if not re.match(r'^[a-z_]+\.[a-z0-9_]+$', device_id):
            raise ValueError(f"Invalid device_id format: {device_id}")
        return device_id

class HabitPredictor:
    VALID_EVENT_TYPES = {"on", "off", "state_change", "trigger"}
    
    def observe(
        self,
        device_id: str,
        event_type: str,
        timestamp: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Observe a device event with validation."""
        if not self.enabled:
            return
        
        # Validate inputs
        try:
            device_id = DeviceEvent.validate_device_id(device_id)
        except ValueError as e:
            _LOGGER.warning("Invalid device_id: %s", e)
            return
        
        if event_type not in self.VALID_EVENT_TYPES:
            _LOGGER.warning("Invalid event_type: %s (expected one of %s)", 
                           event_type, self.VALID_EVENT_TYPES)
            return
        
        if timestamp is None:
            timestamp = time.time()
        elif timestamp < 0 or timestamp > time.time() + 86400:  # Max 1 day in future
            _LOGGER.warning("Invalid timestamp: %s", timestamp)
            return
        
        # Sanitize context
        if context is None:
            context = {}
        context = self._sanitize_context(context)
        
        # ... rest of observe
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Remove potentially sensitive data from context."""
        SENSITIVE_KEYS = {"user_id", "ip_address", "location", "gps", "password", "token"}
        return {
            k: v for k, v in context.items()
            if k.lower() not in SENSITIVE_KEYS and isinstance(v, (str, int, float, bool, list, dict))
        }
```

---

# 📋 ZUSÄTZLICHE MAẞNAHMEN

## 1. Rate Limiting für alle API-Endpoints

```python
# api/middleware.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Apply to endpoints
@bp.post("")
@limiter.limit("10 per minute")
def ingest_event():
    # ...
```

## 2. Input Sanitization für alle User-Inputs

```python
# utils/sanitize.py
import re
from html import escape
from typing import Any, Dict

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input."""
    if not isinstance(value, str):
        raise ValueError("Expected string")
    # Trim whitespace
    value = value.strip()
    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
    # Escape HTML
    value = escape(value)
    return value

def sanitize_dict(d: Dict[str, Any], max_depth: int = 5) -> Dict[str, Any]:
    """Recursively sanitize dictionary."""
    if max_depth <= 0:
        return {}
    
    result = {}
    for key, value in d.items():
        # Sanitize key
        key = sanitize_string(str(key), max_length=100)
        
        # Sanitize value based on type
        if isinstance(value, str):
            result[key] = sanitize_string(value)
        elif isinstance(value, (int, float, bool)):
            result[key] = value
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, max_depth - 1)
        elif isinstance(value, list):
            result[key] = [
                sanitize_string(v) if isinstance(v, str) else v
                for v in value[:100]  # Limit list size
            ]
    
    return result
```

## 3. Audit Logging für kritische Operationen

```python
# utils/audit.py
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

audit_logger = logging.getLogger("audit")

def audit_log(
    action: str,
    user_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
):
    """Log audit trail for security-relevant actions."""
    audit_logger.info(
        "%s | user=%s | entity=%s/%s | success=%s | details=%s",
        action,
        user_id or "anonymous",
        entity_type or "unknown",
        entity_id or "unknown",
        success,
        details or {},
        extra={
            "action": action,
            "user_id": user_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "success": success,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

# Usage:
audit_log(
    action="preference_update",
    user_id="person.john",
    entity_type="user_preference",
    entity_id="light_brightness",
    details={"old_value": 0.7, "new_value": 0.8},
    success=True,
)
```

---

## Performance Monitoring Integration

```python
# utils/performance.py
import time
import functools
import logging
from typing import Callable, Any

performance_logger = logging.getLogger("performance")

def measure_time(operation_name: str):
    """Decorator to measure and log operation time."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                performance_logger.debug(
                    "%s completed in %.2fms", operation_name, duration_ms
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                performance_logger.warning(
                    "%s failed after %.2fms: %s", operation_name, duration_ms, e
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                performance_logger.debug(
                    "%s completed in %.2fms", operation_name, duration_ms
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                performance_logger.warning(
                    "%s failed after %.2fms: %s", operation_name, duration_ms, e
                )
                raise
        
        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

# Usage:
@measure_time("get_neighborhood")
def get_neighborhood(self, center_node: str, hops: int = 1, ...) -> Tuple[...]:
    # ...
```

---

# 🎨 UX-Erweiterungen: Habitus-Zone Dashboard Personalization

## Personalisierte Zone-Konfiguration

```yaml
# habitus_zone_personalization.yaml
schema:
  zone_id: string
  user_preferences:
    - user_id: string
      theme: string  # light, dark, auto
      quick_actions:
        - action_type: string  # light_toggle, climate_set, scene_activate
          entity_id: string
          icon: string
          label: string
          position: int  # Order in UI
      notifications:
        motion_alerts: bool
        energy_alerts: bool
        mood_changes: bool
      automation_preferences:
        auto_lights: bool
        auto_climate: bool
        auto_media: bool
```

## Zone Learning API

```python
# api/v1/zone_learning.py
from flask import Blueprint, jsonify, request

bp = Blueprint("zone_learning", __name__, url_prefix="/zone-learning")

@bp.get("/zones/<zone_id>/suggestions")
def get_zone_suggestions(zone_id: str):
    """Get AI-generated suggestions for zone configuration."""
    # Analyze zone usage patterns
    suggestions = {
        "automations": [
            {
                "trigger": "motion_detected",
                "action": "lights_on",
                "confidence": 0.92,
                "reason": "Motion → Lights activated 92% of the time in last 30 days",
            }
        ],
        "entities": [
            {
                "entity_id": "light.kitchen_main",
                "suggested_role": "primary",
                "confidence": 0.88,
            }
        ],
        "schedules": [
            {
                "time": "07:00",
                "actions": ["lights_on", "temperature_set"],
                "confidence": 0.85,
            }
        ],
    }
    return jsonify({"zone_id": zone_id, "suggestions": suggestions})

@bp.post("/zones/<zone_id>/learn")
def learn_zone_pattern(zone_id: str):
    """Explicitly learn a pattern for the zone."""
    data = request.get_json()
    # Store pattern for ML training
    return jsonify({"status": "learned", "zone_id": zone_id})
```

---

# 📊 FINAL ZUSAMMENFASSUNG

## Issues nach Priorität

| Priority | Count | Category |
|----------|-------|----------|
| **P0** | 6 | Security Vulnerabilities |
| **P1** | 5 | Performance Bottlenecks |
| **P2** | 5 | Code Smells |
| **P3** | 3 | Architectural Debt |

## Estimated Fix Time

| Priority | Issue | Est. Time | Risk |
|----------|-------|-----------|------|
| P0-1 | Auth Token Exposure | 2h | High |
| P0-2 | Input Validation | 4h | High |
| P0-3 | IDOR in Preferences | 3h | High |
| P0-4 | Insecure Default Auth | 2h | High |
| P0-5 | Events API Auth | 1h | High |
| P0-6 | SQL Injection Risk | 2h | Medium |
| P1-1 | N+1 Query Fix | 3h | Medium |
| P1-2 | Cache Bounded | 2h | Medium |
| P1-3 | Async File I/O | 4h | Medium |
| P1-4 | Privacy Leakage | 3h | High |
| P1-5 | Memory Leak | 1h | Low |

**Total P0 Estimated: 14h**
**Total P1 Estimated: 13h**

## Empfohlene Reihenfolge

1. **P0-5** (Events API Auth) - Einfachster Fix, sofortige Wirkung
2. **P0-4** (Default Auth) - Einfach, kritisch
3. **P0-1** (Token Exposure) - Config-Flow Änderung
4. **P0-6** (SQL Injection) - Input Validation
5. **P0-3** (IDOR) - Authorization Check
6. **P0-2** (Input Validation) - Pydantic Schemas
7. **P1-5** (Memory Leak) - Schneller Fix
8. **P1-2** (Cache Bounded) - Einfach
9. **P1-4** (Privacy) - Wichtig für Datenschutz
10. **P1-1** (N+1 Query) - Performance-Kritisch
11. **P1-3** (Async I/O) - Architektur-Änderung

---

*Extended Report generated by Gemini Critical Code Reviewer (2026-02-16 07:40 CET)*