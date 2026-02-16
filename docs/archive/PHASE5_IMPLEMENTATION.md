# Cross-Home Sharing - Phase 5 Implementation

## Overview

This document describes the implementation of Phase 5 Cross-Home Sharing for the CoPilot project.

## Architecture

The implementation follows a modular design with four main components:

```
┌─────────────────────────────────────────────────────────────┐
│                    Cross-Home Sharing                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Discovery   │  │    Sync      │  │   Registry   │      │
│  │   Module     │  │   Protocol   │  │  Registry    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                        │                                     │
│                        ▼                                     │
│                  ┌──────────────┐                            │
│                  │  Conflict    │                            │
│                  │  Resolver    │                            │
│                  └──────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Discovery Module (`discovery.py`)

**Purpose**: Automatic discovery of other CoPilot instances on the network.

**Key Features**:
- mDNS/Bonjour protocol implementation
- Multicast discovery packets
- Service registration and advertisement
- Event-based peer detection

**API**:
```python
discovery = DiscoveryService(home_id, instance_name)
await discovery.start()
await discovery.publish()
peers = discovery.get_peers()
```

### 2. Sync Protocol (`sync.py`)

**Purpose**: WebSocket-based synchronization between homes.

**Key Features**:
- End-to-end encryption
- Message queuing and reliability
- Entity synchronization
- Bidirectional sync support

**API**:
```python
sync = SyncProtocol(peer_id, encryption_key)
await sync.start()
await sync.connect(peer_id)
await sync.sync_entities()
await sync.update_entity(entity_id, data)
```

### 3. Shared Registry (`registry.py`)

**Purpose**: Central registry for shared entities.

**Key Features**:
- Entity registration and management
- Shared-with tracking
- Persistence to storage
- Callback system for updates

**API**:
```python
registry = SharedRegistry()
registry.register(entity_id, shared=True)
registry.share_with(entity_id, home_id)
entities = registry.get_shared()
```

### 4. Conflict Resolver (`conflict.py`)

**Purpose**: Handle conflicts when entities are modified in multiple homes.

**Key Features**:
- Multiple resolution strategies
- Custom strategy support
- Audit trail of conflicts
- Persistence of resolution history

**Strategies**:
- `latest-wins`: Use the most recent version
- `merge`: Merge fields from both versions
- `local-wins`: Always use local version
- `remote-wins`: Always use remote version
- `user-choice`: Mark for user resolution

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Home A    │     │   Home B    │     │   Home C    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │  mDNS Discovery   │                   │
       │──────────────────►│                   │
       │                   │                   │
       │                   │  mDNS Discovery   │
       │                   │──────────────────►│
       │                   │                   │
       │   WebSocket Sync  │                   │
       │◄──────────────────│                   │
       │                   │   WebSocket Sync  │
       │                   │◄──────────────────│
       │                   │                   │
  ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
  │Registry │         │Registry │         │Registry │
  └────┬────┘         └────┬────┘         └────┬────┘
       │                   │                   │
       │   Conflicts       │                   │
       │◄──────────────────│───────────────────│
       │                   │                   │
  ┌────▼────┐
  │Conflict │
  │Resolver │
  └─────────┘
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

## Usage Example

```python
from core.sharing import DiscoveryService, SyncProtocol, SharedRegistry, ConflictResolver

# Initialize
discovery = DiscoveryService(home_id="home-1", instance_name="MyHome")
sync = SyncProtocol(peer_id="home-1", encryption_key="secret-key")
registry = SharedRegistry()
conflict_resolver = ConflictResolver(home_id="home-1")

# Start discovery
await discovery.start()
await discovery.publish()

# Connect to other homes
await sync.connect("home-2", host="192.168.1.100")

# Register entities
registry.register("light.living_room", shared=True, home_id="home-1")
registry.share_with("light.living_room", "home-2")

# Handle updates
await sync.update_entity("light.living_room", {"state": "on"})

# Resolve conflicts
resolved = conflict_resolver.resolve(
    "light.living_room",
    local_version,
    remote_version,
    strategy="latest-wins"
)
```

## Testing

Run the test suite:

```bash
pytest core/sharing/tests/
```

Test coverage:
- Discovery service functionality
- Sync protocol operations
- Registry management
- Conflict resolution strategies
- Integration scenarios

## Future Enhancements

1. **Discovery Optimization**: Add caching and reduced broadcast frequency
2. **Incremental Sync**: Only sync changed entities
3. **Bandwidth Throttling**: Configurable sync rate limiting
4. **Offline Sync**: Queue changes for later sync when offline
5. **Entity Types**: Support for different entity types (scripts, scenes, etc.)
6. **Permission System**: Fine-grained access control per entity
7. **Version History**: Track entity version history

## Security Considerations

1. **Encryption**: All sync traffic uses end-to-end encryption
2. **Authentication**: Peers are authenticated via peer_id verification
3. **Access Control**: Entities can be shared selectively per home
4. **Audit Trail**: All conflicts and resolutions are logged
5. **Key Management**: Secure key distribution and rotation

## Troubleshooting

### Discovery Issues
- Check network multicast support
- Verify firewall allows mDNS traffic (UDP 5353)
- Ensure all homes are on same network segment

### Sync Issues
- Verify WebSocket connections are established
- Check network connectivity between homes
- Review sync logs for error messages

### Conflict Issues
- Review conflict resolution logs
- Consider using different resolution strategy
- Implement custom conflict resolution if needed
