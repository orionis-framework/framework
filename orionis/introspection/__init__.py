from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.introspection.abstract.reflection import ReflectionAbstract
    from orionis.introspection.callables.reflection import ReflectionCallable
    from orionis.introspection.concretes.reflection import ReflectionConcrete
    from orionis.introspection.dependencies.reflection import ReflectDependencies
    from orionis.introspection.instances.reflection import ReflectionInstance
    from orionis.introspection.modules.inspector import ModuleInspector
    from orionis.introspection.modules.reflection import ReflectionModule
    from orionis.introspection.reflection import Reflection

__all__ = [
    "ModuleInspector",
    "ReflectDependencies",
    "Reflection",
    "ReflectionAbstract",
    "ReflectionCallable",
    "ReflectionConcrete",
    "ReflectionInstance",
    "ReflectionModule",
]

_EXPORTS = {
    "ModuleInspector": ("orionis.introspection.modules.inspector", "ModuleInspector"),
    "ReflectDependencies": ("orionis.introspection.dependencies.reflection", "ReflectDependencies"),
    "Reflection": ("orionis.introspection.reflection", "Reflection"),
    "ReflectionAbstract": ("orionis.introspection.abstract.reflection", "ReflectionAbstract"),
    "ReflectionCallable": ("orionis.introspection.callables.reflection", "ReflectionCallable"),
    "ReflectionConcrete": ("orionis.introspection.concretes.reflection", "ReflectionConcrete"),
    "ReflectionInstance": ("orionis.introspection.instances.reflection", "ReflectionInstance"),
    "ReflectionModule": ("orionis.introspection.modules.reflection", "ReflectionModule"),
}

def __getattr__(name: str) -> object:
    """
    Resolve and cache a public package export.

    Parameters
    ----------
    name : str
        Public attribute requested from this package.

    Returns
    -------
    object
        Exported object from its defining module.

    Raises
    ------
    AttributeError
        If the requested attribute is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)

def __dir__() -> list[str]:
    """
    List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
