"""
A/B Testing -- Test automation variants and auto-promote winners.

Runs controlled experiments with two automation variants, measures
user override rate as the outcome metric, and auto-promotes the
variant with statistically significant lower override rate.
"""
from __future__ import annotations

import logging
import math
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("AB_TESTS_DB", "/data/ab_tests.db")

# Minimum observations per variant before significance testing
MIN_SAMPLE_SIZE = 20
# p-value threshold for declaring significance
SIGNIFICANCE_THRESHOLD = 0.05


class ABTestManager:
    """Manage A/B experiments for automation variants.

    Each experiment compares two variants (A and B) of an automation.
    Observations record whether the user *overrode* (manually changed)
    the automation's action.  The variant with the statistically
    significant lower override rate wins and is auto-promoted.

    Statistical test: manual chi-squared (2x2 contingency table) --
    no scipy dependency required.
    """

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path or DB_PATH
        self._lock = threading.Lock()
        self._init_db()
        logger.info("ABTestManager initialized at %s", self._db_path)

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS experiments (
                        id         TEXT PRIMARY KEY,
                        name       TEXT NOT NULL,
                        variant_a  TEXT NOT NULL,
                        variant_b  TEXT NOT NULL,
                        status     TEXT NOT NULL DEFAULT 'running',
                        created_at TEXT NOT NULL,
                        winner     TEXT
                    );

                    CREATE TABLE IF NOT EXISTS observations (
                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                        experiment_id TEXT NOT NULL,
                        variant       TEXT NOT NULL,
                        overridden    INTEGER NOT NULL DEFAULT 0,
                        timestamp     TEXT NOT NULL,
                        FOREIGN KEY (experiment_id) REFERENCES experiments(id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_obs_experiment
                        ON observations(experiment_id);
                """)
                conn.commit()
            finally:
                conn.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now_iso() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_experiment(
        self,
        name: str,
        variant_a_config: dict,
        variant_b_config: dict,
    ) -> str:
        """Create a new A/B experiment. Returns the experiment id."""
        import json

        exp_id = uuid.uuid4().hex[:12]
        now = self._now_iso()

        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    "INSERT INTO experiments "
                    "(id, name, variant_a, variant_b, status, created_at) "
                    "VALUES (?, ?, ?, ?, 'running', ?)",
                    (
                        exp_id,
                        name,
                        json.dumps(variant_a_config),
                        json.dumps(variant_b_config),
                        now,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

        logger.info("Experiment created: %s (%s)", exp_id, name)
        return exp_id

    def record_observation(
        self, experiment_id: str, variant: str, overridden: bool
    ) -> None:
        """Record a single observation for *variant* ('a' or 'b')."""
        now = self._now_iso()
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    "INSERT INTO observations "
                    "(experiment_id, variant, overridden, timestamp) "
                    "VALUES (?, ?, ?, ?)",
                    (experiment_id, variant.lower(), int(overridden), now),
                )
                conn.commit()
            finally:
                conn.close()

    def check_significance(self, experiment_id: str) -> Dict[str, Any]:
        """Run a chi-squared test on the collected observations.

        Returns
        -------
        dict
            ``significant``, ``winner``, ``p_value``,
            ``sample_size_a``, ``sample_size_b``.
        """
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                rows = conn.execute(
                    "SELECT variant, overridden FROM observations "
                    "WHERE experiment_id = ?",
                    (experiment_id,),
                ).fetchall()
            finally:
                conn.close()

        # Tallies
        a_total = a_overridden = 0
        b_total = b_overridden = 0
        for variant, overridden in rows:
            if variant == "a":
                a_total += 1
                a_overridden += overridden
            else:
                b_total += 1
                b_overridden += overridden

        result: Dict[str, Any] = {
            "significant": False,
            "winner": None,
            "p_value": 1.0,
            "sample_size_a": a_total,
            "sample_size_b": b_total,
            "override_rate_a": round(a_overridden / a_total, 4) if a_total else None,
            "override_rate_b": round(b_overridden / b_total, 4) if b_total else None,
        }

        if a_total < MIN_SAMPLE_SIZE or b_total < MIN_SAMPLE_SIZE:
            return result

        # 2x2 contingency table chi-squared (Yates-corrected)
        p_value = self._chi_squared_2x2(
            a_overridden, a_total - a_overridden,
            b_overridden, b_total - b_overridden,
        )
        result["p_value"] = round(p_value, 6)

        if p_value < SIGNIFICANCE_THRESHOLD:
            result["significant"] = True
            rate_a = a_overridden / a_total
            rate_b = b_overridden / b_total
            result["winner"] = "a" if rate_a < rate_b else "b"

        return result

    def promote_winner(self, experiment_id: str) -> Dict[str, Any]:
        """Promote the winning variant and close the experiment."""
        sig = self.check_significance(experiment_id)

        if not sig["significant"]:
            return {
                "promoted": False,
                "reason": "No statistically significant winner yet",
                **sig,
            }

        winner = sig["winner"]

        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                conn.execute(
                    "UPDATE experiments SET status = 'completed', winner = ? "
                    "WHERE id = ?",
                    (winner, experiment_id),
                )
                conn.commit()
            finally:
                conn.close()

        logger.info(
            "Experiment %s completed -- winner: variant %s (p=%.4f)",
            experiment_id, winner, sig["p_value"],
        )
        return {"promoted": True, "winner": winner, **sig}

    def list_experiments(self) -> List[Dict[str, Any]]:
        """Return all experiments with their current status."""
        import json

        with self._lock:
            conn = sqlite3.connect(self._db_path)
            try:
                rows = conn.execute(
                    "SELECT id, name, variant_a, variant_b, status, "
                    "created_at, winner FROM experiments "
                    "ORDER BY created_at DESC"
                ).fetchall()
            finally:
                conn.close()

        return [
            {
                "id": r[0],
                "name": r[1],
                "variant_a": json.loads(r[2]),
                "variant_b": json.loads(r[3]),
                "status": r[4],
                "created_at": r[5],
                "winner": r[6],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Chi-squared (manual, no scipy)
    # ------------------------------------------------------------------

    @staticmethod
    def _chi_squared_2x2(a: int, b: int, c: int, d: int) -> float:
        """Yates-corrected chi-squared p-value for a 2x2 table.

        Table layout::

                    overridden  not-overridden
            var_a       a             b
            var_b       c             d

        Returns an approximate p-value using the survival function of
        the chi-squared distribution with 1 degree of freedom.
        """
        n = a + b + c + d
        if n == 0:
            return 1.0

        # Yates correction
        numerator = n * (abs(a * d - b * c) - n / 2.0) ** 2
        denom = (a + b) * (c + d) * (a + c) * (b + d)
        if denom == 0:
            return 1.0

        chi2 = numerator / denom

        # Approximate p-value: P(X > chi2) for X ~ chi-sq(1)
        # Using the complementary error function relationship:
        #   P(X > x) ~= erfc(sqrt(x/2)) for df=1
        p = math.erfc(math.sqrt(chi2 / 2.0))
        return max(0.0, min(1.0, p))
