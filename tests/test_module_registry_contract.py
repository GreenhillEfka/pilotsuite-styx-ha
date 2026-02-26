"""Runtime registry contract checks for Copilot modules."""

from __future__ import annotations

import ast
from pathlib import Path


def _load_module_specs() -> tuple[dict[str, tuple[str, str]], list[str], Path]:
    root = Path(__file__).resolve().parents[1] / "custom_components" / "ai_home_copilot"
    init_path = root / "__init__.py"
    tree = ast.parse(init_path.read_text(encoding="utf-8"))

    module_imports: dict[str, tuple[str, str]] | None = None
    modules_list: list[str] | None = None

    # Collect tier lists for combining into _MODULES
    tier_lists: dict[str, list[str]] = {}

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if name == "_MODULE_IMPORTS":
                module_imports = ast.literal_eval(node.value)
            elif name == "_MODULES":
                # _MODULES may be a plain list or a BinOp concatenation
                try:
                    modules_list = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    # Build from tier lists that were already parsed
                    modules_list = []
                    for tier_name in ("_TIER_0_KERNEL", "_TIER_1_BRAIN", "_TIER_2_CONTEXT", "_TIER_3_EXTENSIONS"):
                        modules_list.extend(tier_lists.get(tier_name, []))
            elif name.startswith("_TIER_"):
                try:
                    tier_lists[name] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    pass

    assert module_imports is not None
    assert modules_list is not None
    return module_imports, modules_list, root


def test_module_registry_lists_are_consistent() -> None:
    module_imports, modules_list, _root = _load_module_specs()
    assert sorted(module_imports.keys()) == sorted(modules_list)


def test_registered_modules_follow_runtime_contract() -> None:
    """All registered modules must be constructible without required args and
    expose runtime lifecycle methods with the expected signature.
    """

    module_imports, _modules_list, root = _load_module_specs()
    failures: list[str] = []

    for name, (module_path, class_name) in module_imports.items():
        if not module_path.startswith(".core.modules."):
            failures.append(f"{name}: unsupported module path {module_path}")
            continue

        rel = module_path.replace(".core.modules.", "core/modules/") + ".py"
        path = root / rel
        if not path.exists():
            failures.append(f"{name}: file missing ({path})")
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"))
        cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name), None)
        if cls is None:
            failures.append(f"{name}: class missing ({class_name})")
            continue

        init_fn = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)
        if init_fn is not None:
            positional = init_fn.args.args[1:]  # skip self
            required = len(positional) - len(init_fn.args.defaults)
            if required > 0:
                required_names = [arg.arg for arg in positional[:required]]
                failures.append(f"{name}: __init__ requires args {required_names}")

        setup_fn = next(
            (n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "async_setup_entry"),
            None,
        )
        unload_fn = next(
            (n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "async_unload_entry"),
            None,
        )

        if setup_fn is None:
            failures.append(f"{name}: async_setup_entry missing")
        elif len(setup_fn.args.args) != 2:
            failures.append(f"{name}: async_setup_entry arg count invalid")

        if unload_fn is None:
            failures.append(f"{name}: async_unload_entry missing")
        elif len(unload_fn.args.args) != 2:
            failures.append(f"{name}: async_unload_entry arg count invalid")

    assert not failures, " ; ".join(failures)

