# Core Add-on Integration

This directory contains the core sharing functionality for CoPilot Cross-Home Sharing (Phase 5).

## Structure

```
core/sharing/
├── __init__.py       # Package exports
├── README.md         # Feature documentation
├── discovery.py      # mDNS/Bonjour discovery
├── sync.py           # WebSocket sync protocol
├── registry.py       # Shared entity registry
├── conflict.py       # Conflict resolution
└── tests/            # Unit tests (see separate section)
```

## Integration with HA Copilot

The sharing module is designed to be integrated into the main CoPilot core. Key integration points:

### 1. Discovery Integration

```python
# In core/copilot.py
from core.sharing.discovery import DiscoveryService

class CoPilotCore:
    def __init__(self, home_id: str):
        self.discovery = DiscoveryService(home_id, "CoPilot")
```

### 2. Sync Protocol Integration

```python
# In core/copilot.py
from core.sharing.sync import SyncProtocol

class CoPilotCore:
    def __init__(self, home_id: str):
        self.sync = SyncProtocol(home_id, encryption_key)
        self.sync.on_sync_complete(self._on_sync_complete)
```

### 3. Shared Registry Integration

```python
# In core/copilot.py
from core.sharing.registry import SharedRegistry

class CoPilotCore:
    def __init__(self, home_id: str):
        self.registry = SharedRegistry()
        self.registry.register_callback(on_updated=self._on_entity_update)
```

### 4. Conflict Resolution Integration

```python
# In core/copilot.py
from core.sharing.conflict import ConflictResolver

class CoPilotCore:
    def __init__(self, home_id: str):
        self.conflict_resolver = ConflictResolver(home_id)
```

## Configuration

Add to `configuration.yaml`:

```yaml
copilot:
  sharing:
    enabled: true
    discovery:
      enabled: true
      port: 5353
    sync:
      enabled: true
      port: 8765
      encryption:
        enabled: true
        key_path: /config/.copilot/sharing_key
    conflict_resolution:
      strategy: latest-wins
```

## Security Considerations

1. **Encryption**: All sync traffic uses end-to-end encryption with per-session keys
2. **Authentication**: Peers are authenticated via peer_id verification
3. **Access Control**: Entities can be shared selectively per home
4. **Audit Trail**: All conflicts and resolutions are logged

## Testing

Run tests with:

```bash
pytest core/sharing/tests/
```

See `tests/core/sharing/` for test coverage.

## Development Notes

- All components use async/await for non-blocking operations
- Callback-based event system for loose coupling
- Storage persistence for registry and conflict state
- Configuration-driven strategy selection for conflict resolution
