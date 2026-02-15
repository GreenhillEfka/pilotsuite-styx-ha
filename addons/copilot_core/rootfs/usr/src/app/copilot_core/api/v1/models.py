"""API v1 Models - Stub for User Hints."""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


class HintStatus(str, Enum):
    """Hint status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class HintType(str, Enum):
    """Hint type enumeration."""
    AUTOMATION = "automation"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    INFO = "info"


@dataclass
class HintData:
    """Hint data structure."""
    hint_id: str
    title: str
    description: str
    hint_type: HintType
    status: HintStatus
    entity_ids: list[str]
    confidence: float
    metadata: dict
