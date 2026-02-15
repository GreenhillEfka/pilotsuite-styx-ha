"""Shared Entity Registry for CoPilot Cross-Home Sharing."""

import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable, Set
from dataclasses import dataclass, field, asdict
import hashlib


@dataclass
class SharedEntity:
    """Represents a shared entity."""

    entity_id: str
    name: str
    domain: str
    shared: bool = True
    last_updated: str = ""
    last_updated_by: str = ""
    shared_with: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SharedEntity":
        """Create from dictionary."""
        return cls(
            entity_id=data["entity_id"],
            name=data["name"],
            domain=data["domain"],
            shared=data.get("shared", True),
            last_updated=data.get("last_updated", ""),
            last_updated_by=data.get("last_updated_by", ""),
            shared_with=data.get("shared_with", []),
            metadata=data.get("metadata", {}),
        )


class SharedRegistry:
    """Registry for shared entities between homes."""

    def __init__(self, storage_path: str = "/config/.copilot/sharing_registry.json"):
        """Initialize shared registry."""
        self.storage_path = storage_path
        self._entities: Dict[str, SharedEntity] = {}
        self._shared_with_home_ids: Dict[str, Set[str]] = {}
        self._entity_updated_callbacks: List[
            Callable[[str, SharedEntity, Optional[SharedEntity]], None]
        ] = []
        self._entity_registered_callbacks: List[Callable[[SharedEntity], None]] = []
        self._entity_unregistered_callbacks: List[Callable[[str], None]] = []

    def register(
        self,
        entity_id: str,
        shared: bool = True,
        home_id: Optional[str] = None,
        **metadata,
    ) -> SharedEntity:
        """Register an entity for sharing."""
        entity = self._entities.get(entity_id)

        if entity:
            # Update existing entity
            entity.shared = shared
            entity.metadata.update(metadata)
            entity.last_updated = datetime.utcnow().isoformat()
            if home_id:
                entity.last_updated_by = home_id

            # Track shared with
            if home_id and shared:
                if entity_id not in self._shared_with_home_ids:
                    self._shared_with_home_ids[entity_id] = set()
                self._shared_with_home_ids[entity_id].add(home_id)
        else:
            # Create new entity
            # Extract domain from entity_id (e.g., "light.living_room" -> "light")
            domain = entity_id.split(".")[0] if "." in entity_id else "unknown"

            entity = SharedEntity(
                entity_id=entity_id,
                name=entity_id.replace("_", " ").title(),
                domain=domain,
                shared=shared,
                last_updated=datetime.utcnow().isoformat(),
                shared_with=[home_id] if home_id and shared else [],
                metadata=metadata,
            )

            if home_id and shared:
                self._shared_with_home_ids[entity_id] = {home_id}

        self._entities[entity_id] = entity

        # Notify callbacks
        for callback in self._entity_registered_callbacks:
            try:
                callback(entity)
            except Exception as e:
                print(f"Entity registered callback error: {e}")

        self._save()

        return entity

    def unregister(self, entity_id: str) -> None:
        """Unregister an entity from sharing."""
        if entity_id in self._entities:
            entity = self._entities[entity_id]
            entity.shared = False

            # Notify callbacks
            for callback in self._entity_unregistered_callbacks:
                try:
                    callback(entity_id)
                except Exception as e:
                    print(f"Entity unregistered callback error: {e}")

            # Remove from shared_with tracking
            self._shared_with_home_ids.pop(entity_id, None)

            del self._entities[entity_id]
            self._save()

    def update(self, entity_id: str, shared: Optional[bool] = None, **metadata) -> SharedEntity:
        """Update an entity's sharing configuration."""
        if entity_id not in self._entities:
            raise ValueError(f"Entity {entity_id} not registered")

        entity = self._entities[entity_id]
        old_entity = entity.to_dict()

        if shared is not None:
            entity.shared = shared

        if metadata:
            entity.metadata.update(metadata)

        entity.last_updated = datetime.utcnow().isoformat()

        self._entities[entity_id] = entity

        # Notify callbacks
        for callback in self._entity_updated_callbacks:
            try:
                callback(entity_id, entity, old_entity)
            except Exception as e:
                print(f"Entity updated callback error: {e}")

        self._save()

        return entity

    def get(self, entity_id: str) -> Optional[SharedEntity]:
        """Get a specific entity."""
        return self._entities.get(entity_id)

    def get_all(self) -> Dict[str, SharedEntity]:
        """Get all registered entities."""
        return self._entities.copy()

    def get_shared(self) -> Dict[str, SharedEntity]:
        """Get all shared entities."""
        return {
            entity_id: entity
            for entity_id, entity in self._entities.items()
            if entity.shared
        }

    def get_shared_with(self, entity_id: str) -> Set[str]:
        """Get list of home IDs this entity is shared with."""
        return self._shared_with_home_ids.get(entity_id, set()).copy()

    def share_with(self, entity_id: str, home_id: str) -> None:
        """Share an entity with another home."""
        if entity_id not in self._entities:
            raise ValueError(f"Entity {entity_id} not registered")

        entity = self._entities[entity_id]
        entity.shared_with.append(home_id)

        if entity_id not in self._shared_with_home_ids:
            self._shared_with_home_ids[entity_id] = set()
        self._shared_with_home_ids[entity_id].add(home_id)

        entity.last_updated = datetime.utcnow().isoformat()
        self._save()

    def stop_sharing_with(self, entity_id: str, home_id: str) -> None:
        """Stop sharing an entity with a home."""
        if entity_id not in self._entities:
            return

        entity = self._entities[entity_id]
        if home_id in entity.shared_with:
            entity.shared_with.remove(home_id)

        if entity_id in self._shared_with_home_ids:
            self._shared_with_home_ids[entity_id].discard(home_id)

        entity.last_updated = datetime.utcnow().isoformat()
        self._save()

    def is_shared(self, entity_id: str) -> bool:
        """Check if an entity is shared."""
        entity = self._entities.get(entity_id)
        return entity is not None and entity.shared

    def register_callback(
        self,
        on_updated: Optional[
            Callable[[str, SharedEntity, Optional[SharedEntity]], None]
        ] = None,
        on_registered: Optional[Callable[[SharedEntity], None]] = None,
        on_unregistered: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Register entity registry callbacks."""
        if on_updated:
            self._entity_updated_callbacks.append(on_updated)
        if on_registered:
            self._entity_registered_callbacks.append(on_registered)
        if on_unregistered:
            self._entity_unregistered_callbacks.append(on_unregistered)

    def _save(self) -> None:
        """Save registry to storage."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

            data = {
                "entities": {
                    entity_id: entity.to_dict()
                    for entity_id, entity in self._entities.items()
                },
                "shared_with": {
                    entity_id: list(home_ids)
                    for entity_id, home_ids in self._shared_with_home_ids.items()
                },
            }

            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Registry save error: {e}")

    def _load(self) -> None:
        """Load registry from storage."""
        if not os.path.exists(self.storage_path):
            return

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)

            # Load entities
            for entity_id, entity_data in data.get("entities", {}).items():
                self._entities[entity_id] = SharedEntity.from_dict(entity_data)

            # Load shared_with tracking
            for entity_id, home_ids in data.get("shared_with", {}).items():
                self._shared_with_home_ids[entity_id] = set(home_ids)

        except Exception as e:
            print(f"Registry load error: {e}")

    def clear(self) -> None:
        """Clear all shared entities."""
        self._entities.clear()
        self._shared_with_home_ids.clear()
        self._save()


# Singleton instance
_registry: Optional[SharedRegistry] = None


def get_registry(storage_path: str = "/config/.copilot/sharing_registry.json") -> SharedRegistry:
    """Get or create the shared registry singleton."""
    global _registry
    if _registry is None:
        _registry = SharedRegistry(storage_path)
        _registry._load()
    return _registry
