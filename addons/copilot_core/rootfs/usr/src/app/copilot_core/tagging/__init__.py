"""Tagging primitives for AI Home CoPilot."""

from .models import Tag, TagDisplay, TagGovernance, TagHAConfig
from .registry import TagRegistry, TagRegistryError
from .assignments import (
    ALLOWED_SUBJECT_KINDS,
    TagAssignment,
    TagAssignmentStore,
    TagAssignmentStoreError,
    TagAssignmentValidationError,
)

__all__ = [
    "Tag",
    "TagDisplay",
    "TagGovernance",
    "TagHAConfig",
    "TagRegistry",
    "TagRegistryError",
    "ALLOWED_SUBJECT_KINDS",
    "TagAssignment",
    "TagAssignmentStore",
    "TagAssignmentStoreError",
    "TagAssignmentValidationError",
]
