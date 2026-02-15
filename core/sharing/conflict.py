"""Conflict Resolution for CoPilot Cross-Home Sharing."""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
import hashlib


@dataclass
class Conflict:
    """Represents a conflict between entity versions."""

    entity_id: str
    local_version: Dict[str, Any]
    remote_version: Dict[str, Any]
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None


class ConflictResolver:
    """Handles conflict resolution for shared entities."""

    def __init__(self, home_id: str, storage_path: str = "/config/.copilot/conflicts.json"):
        """Initialize conflict resolver."""
        self.home_id = home_id
        self.storage_path = storage_path
        self._active_conflicts: Dict[str, Conflict] = {}
        self._resolution_strategies: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = {
            "latest-wins": self._latest_wins,
            "merge": self._merge,
            "local-wins": self._local_wins,
            "remote-wins": self._remote_wins,
            "user-choice": self._user_choice,
        }
        self._custom_strategies: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]] = {}
        self._conflict_detected_callbacks: List[Callable[[Conflict], None]] = []

    def register_strategy(self, name: str, callback: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]) -> None:
        """Register a custom resolution strategy."""
        self._custom_strategies[name] = callback

    def resolve(
        self,
        entity_id: str,
        local_version: Dict[str, Any],
        remote_version: Dict[str, Any],
        strategy: str = "latest-wins",
    ) -> Dict[str, Any]:
        """Resolve a conflict between local and remote versions."""
        # Check if this is a real conflict
        if self._is_identical(local_version, remote_version):
            return local_version

        # Create conflict record
        conflict = Conflict(
            entity_id=entity_id,
            local_version=local_version,
            remote_version=remote_version,
        )

        # Use requested strategy
        resolver = self._custom_strategies.get(strategy) or self._resolution_strategies.get(strategy)

        if not resolver:
            # Default to latest-wins
            resolver = self._latest_wins

        resolved = resolver(local_version, remote_version)

        # Record resolution
        conflict.resolution = strategy
        conflict.resolved_by = self.home_id
        conflict.resolved_at = datetime.utcnow().isoformat()

        self._active_conflicts[entity_id] = conflict
        self._save()

        # Notify callbacks
        for callback in self._conflict_detected_callbacks:
            try:
                callback(conflict)
            except Exception as e:
                print(f"Conflict callback error: {e}")

        return resolved

    def _latest_wins(
        self, local: Dict[str, Any], remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use the most recent version."""
        local_time = local.get("last_updated", "")
        remote_time = remote.get("last_updated", "")

        # If no timestamps, use remote
        if not local_time and not remote_time:
            return remote

        if not local_time:
            return remote

        if not remote_time:
            return local

        # Compare timestamps
        try:
            local_dt = datetime.fromisoformat(local_time.replace("Z", "+00:00"))
            remote_dt = datetime.fromisoformat(remote_time.replace("Z", "+00:00"))

            if local_dt >= remote_dt:
                return local
            return remote
        except Exception:
            # If parsing fails, default to remote
            return remote

    def _merge(
        self, local: Dict[str, Any], remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge versions, taking newer values for each field."""
        merged = {}

        # Get all keys from both versions
        all_keys = set(local.keys()) | set(remote.keys())

        for key in all_keys:
            local_val = local.get(key)
            remote_val = remote.get(key)

            # If only in one version, use that
            if local_val is None:
                merged[key] = remote_val
            elif remote_val is None:
                merged[key] = local_val
            else:
                # Both have value - use latest
                local_time = local.get("last_updated", "")
                remote_time = remote.get("last_updated", "")

                if not local_time or (remote_time and remote_time > local_time):
                    merged[key] = remote_val
                else:
                    merged[key] = local_val

        # Preserve metadata
        if "last_updated" in local and "last_updated" in remote:
            merged["last_updated"] = max(
                local["last_updated"], remote["last_updated"]
            )

        return merged

    def _local_wins(
        self, local: Dict[str, Any], remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Always use local version."""
        return local

    def _remote_wins(
        self, local: Dict[str, Any], remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Always use remote version."""
        return remote

    def _user_choice(
        self, local: Dict[str, Any], remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mark conflict for user resolution."""
        return local  # Keep local for now

    def _is_identical(self, local: Dict[str, Any], remote: Dict[str, Any]) -> bool:
        """Check if two versions are identical."""
        # Compare relevant fields
        compare_keys = {"state", "attributes", "last_updated", "last_changed"}

        local_relevant = {k: v for k, v in local.items() if k in compare_keys}
        remote_relevant = {k: v for k, v in remote.items() if k in compare_keys}

        return local_relevant == remote_relevant

    def get_conflict(self, entity_id: str) -> Optional[Conflict]:
        """Get conflict record for an entity."""
        return self._active_conflicts.get(entity_id)

    def get_active_conflicts(self) -> Dict[str, Conflict]:
        """Get all active conflicts."""
        return self._active_conflicts.copy()

    def clear_conflict(self, entity_id: str) -> None:
        """Clear a resolved conflict."""
        if entity_id in self._active_conflicts:
            del self._active_conflicts[entity_id]
            self._save()

    def clear_all_conflicts(self) -> None:
        """Clear all conflicts."""
        self._active_conflicts.clear()
        self._save()

    def register_conflict_callback(self, callback: Callable[[Conflict], None]) -> None:
        """Register callback for conflict detection."""
        self._conflict_detected_callbacks.append(callback)

    def _save(self) -> None:
        """Save conflicts to storage."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

            data = {
                "conflicts": {
                    entity_id: {
                        "entity_id": c.entity_id,
                        "local_version": c.local_version,
                        "remote_version": c.remote_version,
                        "resolution": c.resolution,
                        "resolved_by": c.resolved_by,
                        "resolved_at": c.resolved_at,
                    }
                    for entity_id, c in self._active_conflicts.items()
                }
            }

            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Conflict save error: {e}")

    def _load(self) -> None:
        """Load conflicts from storage."""
        if not os.path.exists(self.storage_path):
            return

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)

            for entity_id, conflict_data in data.get("conflicts", {}).items():
                self._active_conflicts[entity_id] = Conflict(
                    entity_id=conflict_data["entity_id"],
                    local_version=conflict_data["local_version"],
                    remote_version=conflict_data["remote_version"],
                    resolution=conflict_data.get("resolution"),
                    resolved_by=conflict_data.get("resolved_by"),
                    resolved_at=conflict_data.get("resolved_at"),
                )

        except Exception as e:
            print(f"Conflict load error: {e}")


# Singleton instance
_resolver: Optional[ConflictResolver] = None


def get_resolver(home_id: str = "default", storage_path: str = "/config/.copilot/conflicts.json") -> ConflictResolver:
    """Get or create the conflict resolver singleton."""
    global _resolver
    if _resolver is None:
        _resolver = ConflictResolver(home_id, storage_path)
        _resolver._load()
    return _resolver
