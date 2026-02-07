"""Core runtime for ai_home_copilot.

This package intentionally contains only lightweight plumbing:
- module interface
- registry
- runtime container

Behavior is implemented in modules (e.g. the legacy module) so we can
incrementally refactor without changing user-visible behavior.
"""

from __future__ import annotations
