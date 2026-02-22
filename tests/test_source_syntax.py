"""Static syntax guard for the integration source tree."""

from __future__ import annotations

import ast
from pathlib import Path


def test_ai_home_copilot_sources_are_valid_python() -> None:
    """Prevent shipping syntax/indentation regressions in module files."""
    source_root = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "ai_home_copilot"
    )
    failures: list[str] = []

    for path in sorted(source_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as err:
            failures.append(f"{path.relative_to(source_root)}:{err.lineno}:{err.msg}")

    assert not failures, " ; ".join(failures)
