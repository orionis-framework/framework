# ruff: noqa: TC003
# Keep discovery path annotations available to runtime reflection.
"""Discover file-owned migration and seeder classes with stable persisted names."""

from pathlib import Path
from orionis.introspection.modules.inspector import ModuleInspector
from orionis.introspection.modules.reflection import ReflectionModule


def _discover_steps[T](
    base_path: Path,
    target_path: Path,
    step_base: type[T],
    kind: str,
) -> dict[str, type[T]]:
    """Collect distinct step classes while rejecting ambiguous persisted names.

    Parameters
    ----------
    base_path : pathlib.Path
        Application root containing the discovery directory.
    target_path : pathlib.Path
        Directory containing migration or seeder modules.
    step_base : type[``T``]
        Required base class for eligible definitions.
    kind : str
        Step category used in ambiguity diagnostics.

    Returns
    -------
    dict[str, type[``T``]]
        File stems mapped to their own classes, sorted by persisted name.

    Raises
    ------
    OSError
        If the directory cannot be traversed completely.
    ValueError
        If the directory is outside the application or distinct classes share a name.
    """
    modules = ModuleInspector.discoverModules(base_path, target_path)
    found: dict[str, type[T]] = {}
    for module_name in sorted(modules):
        stem = module_name.rsplit(".", 1)[-1]
        if stem == "__init__":
            continue
        module = ReflectionModule(module_name)
        if hasattr(module.getModule(), "__path__"):
            continue
        for candidate in module.getClasses().values():
            if candidate.__module__ != module_name or not issubclass(
                candidate,
                step_base,
            ):
                continue
            previous = found.get(stem)
            if previous is not None and previous is not candidate:
                message = (
                    f"Ambiguous {kind} '{stem}': "
                    f"{previous.__module__}.{previous.__name__} and "
                    f"{module_name}.{candidate.__name__}."
                )
                raise ValueError(message)
            found[stem] = candidate
    return dict(sorted(found.items()))
