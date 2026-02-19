"""
Module Registry -- Persistent module state management.

Tracks per-module state (active/learning/off) with SQLite persistence.
The dashboard UI and API use this to control which modules are active.

States:
  - active:   Module is fully operational (default for all modules)
  - learning: Module collects data but does not act on it
  - off:      Module is disabled entirely

Thread-safe singleton with SQLite persistence under /data/.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Dict, Optional

_LOGGER = logging.getLogger(__name__)

DB_PATH = os.environ.get("MODULE_STATES_DB", "/data/module_states.db")

VALID_STATES = frozenset({"active", "learning", "off"})
DEFAULT_STATE = "active"


class ModuleRegistry:
    """Thread-safe, singleton module state registry with SQLite persistence.

    Usage::

        registry = ModuleRegistry.get_instance()
        registry.set_state("mood_engine", "learning")
        assert registry.is_learning("mood_engine")
    """

    _instance: Optional[ModuleRegistry] = None
    _instance_lock = threading.Lock()

    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path or DB_PATH
        self._lock = threading.Lock()
        self._init_db()
        _LOGGER.info("ModuleRegistry initialized at %s", self._db_path)

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls, db_path: str | None = None) -> ModuleRegistry:
        """Return the singleton ModuleRegistry, creating it on first call.

        Uses double-checked locking for thread safety.
        """
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls(db_path=db_path)
        return cls._instance

    @classmethod
    def _reset_instance(cls) -> None:
        """Reset the singleton (testing only)."""
        with cls._instance_lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Database setup
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create the module_states table if it does not exist."""
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS module_states (
                        module_id   TEXT PRIMARY KEY,
                        state       TEXT NOT NULL DEFAULT 'active',
                        updated_at  TEXT NOT NULL
                    )
                """)
                conn.commit()
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now_iso() -> str:
        """Return current UTC timestamp in ISO-8601 format."""
        return datetime.now(timezone.utc).isoformat()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection (caller must close)."""
        return sqlite3.connect(self._db_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_state(self, module_id: str) -> str:
        """Return the state of *module_id*.

        Returns ``"active"`` if the module has never been explicitly configured.
        """
        with self._lock:
            conn = self._get_connection()
            try:
                row = conn.execute(
                    "SELECT state FROM module_states WHERE module_id = ?",
                    (module_id,),
                ).fetchone()
                return row[0] if row else DEFAULT_STATE
            finally:
                conn.close()

    def set_state(self, module_id: str, state: str) -> bool:
        """Persist a new state for *module_id*.

        Args:
            module_id: Identifier of the module (e.g. ``"mood_engine"``).
            state: One of ``"active"``, ``"learning"``, ``"off"``.

        Returns:
            ``True`` if the state was accepted and persisted,
            ``False`` if *state* is invalid.
        """
        if state not in VALID_STATES:
            _LOGGER.warning(
                "Rejected invalid state %r for module %s (valid: %s)",
                state, module_id, ", ".join(sorted(VALID_STATES)),
            )
            return False

        now = self._now_iso()
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute(
                    """
                    INSERT INTO module_states (module_id, state, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(module_id) DO UPDATE
                        SET state = excluded.state,
                            updated_at = excluded.updated_at
                    """,
                    (module_id, state, now),
                )
                conn.commit()
                _LOGGER.info("Module %s -> %s", module_id, state)
                return True
            except sqlite3.Error:
                _LOGGER.exception("Failed to persist state for %s", module_id)
                return False
            finally:
                conn.close()

    def get_all_states(self) -> Dict[str, str]:
        """Return a mapping of every explicitly-configured module to its state.

        Modules that have never been configured will *not* appear here
        (their implicit state is ``"active"``).
        """
        with self._lock:
            conn = self._get_connection()
            try:
                rows = conn.execute(
                    "SELECT module_id, state FROM module_states ORDER BY module_id"
                ).fetchall()
                return {module_id: state for module_id, state in rows}
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Convenience predicates
    # ------------------------------------------------------------------

    def is_active(self, module_id: str) -> bool:
        """Return ``True`` if the module is in ``"active"`` state."""
        return self.get_state(module_id) == "active"

    def is_learning(self, module_id: str) -> bool:
        """Return ``True`` if the module is in ``"learning"`` state."""
        return self.get_state(module_id) == "learning"

    def is_off(self, module_id: str) -> bool:
        """Return ``True`` if the module is in ``"off"`` state."""
        return self.get_state(module_id) == "off"
