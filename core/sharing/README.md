# Cross-Home Sharing (Phase 5)

Diese Komponente implementiert Multi-Home Sync und Shared Entities.

## Features

- **mDNS/Bonjour Discovery** - Automatische Erkennung anderer CoPilot-Instanzen im Netzwerk
- **WebSocket-basierte Sync** - Echtzeit-Synchronisation zwischen Homes
- **End-to-End Encryption** - Sicherer Austausch von Entity-Daten
- **Merge-Strategien** - Konfliktlösung bei gleichzeitigen Änderungen

## Architecture

```
┌─────────────────┐     mDNS/Bonjour      ┌─────────────────┐
│   Home A        │ ◄─────────────────►   │   Home B        │
│  CoPilot Core   │     WebSocket Sync     │  CoPilot Core   │
│  ┌──────────┐   │                       │  ┌──────────┐   │
│  │Discovery │   │   ┌─────────────┐     │  │Discovery │   │
│  │ Module   │◄──┼───►│  Sync     │◄─────┼──►│ Module   │   │
│  └──────────┘   │   │ Protocol    │     │  └──────────┘   │
│                 │   └─────────────┘     │                 │
│  ┌──────────┐   │   ┌─────────────┐     │  ┌──────────┐   │
│  │ Shared   │   │   │ Merge       │     │  │ Shared   │   │
│  │ Registry │◄──┼───►│ Strategies  │◄────┼──►│ Registry │   │
│  └──────────┘   │   └─────────────┘     │  └──────────┘   │
└─────────────────┘                       └─────────────────┘
```

## Components

### 1. Discovery Module

Auto-discovery via mDNS/Bonjour:

```python
from sharing.discovery import DiscoveryService

discovery = DiscoveryService()
await discovery.start()
await discovery.publish()
```

### 2. Sync Protocol

WebSocket-basierter Sync mit End-to-End Encryption:

```python
from sharing.sync import SyncProtocol

sync = SyncProtocol(peer_id, encryption_key)
await sync.connect()
await sync.sync_entities()
```

### 3. Shared Registry

Zentrale Registry für geteilte Entities:

```python
from sharing.registry import SharedRegistry

registry = SharedRegistry()
registry.register("light.living_room", shared=True)
```

### 4. Conflict Resolution

Mehrere Merge-Strategien verfügbar:

- `latest-wins` - Neueste Änderung gewinnt
- `merge` - Automatische Zusammenführung
- `user-choice` - Benutzerauswahl
- `custom` - benutzerdefinierte Strategie

## API

### Discovery

- `discover_peers()` - Suche nach anderen CoPilot-Instanzen
- `publish_self()` - Veröffentliche eigene Instanz
- `on_peer_discovered(callback)` - Event für neue Peers

### Sync

- `connect(peer_id)` - Verbinde mit Peer
- `sync_entities()` - Synchronisiere Entities
- `update_entity(entity_id, data)` - Update einer Entity
- `on_sync_complete(callback)` - Event bei Sync-Ende

### Registry

- `register(entity_id, shared=False)` - Entity registrieren
- `unregister(entity_id)` - Entity deregistrieren
- `get_shared()` - Hole alle geteilten Entities
- `on_entity_updated(callback)` - Event bei Update

## Konfiguration

```yaml
# configuration.yaml
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

## Test

```bash
pytest tests/core/sharing/
```
