from __future__ import annotations

from collections.abc import Callable

from .module import CopilotModule


ModuleFactory = Callable[[], CopilotModule]


class ModuleRegistry:
    """Simple registry of module factories.

    Intentionally tiny. We can grow this as modules become configurable.
    """

    def __init__(self) -> None:
        self._factories: dict[str, ModuleFactory] = {}

    def register(self, name: str, factory: ModuleFactory) -> None:
        if name in self._factories:
            raise ValueError(f"Module already registered: {name}")
        self._factories[name] = factory

    def create(self, name: str) -> CopilotModule:
        try:
            factory = self._factories[name]
        except KeyError as err:
            raise KeyError(f"Unknown module: {name}") from err
        return factory()

    def names(self) -> list[str]:
        return sorted(self._factories)
