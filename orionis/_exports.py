from importlib import import_module

def resolve_export(
    namespace: dict[str, object],
    exports: dict[str, tuple[str, str]],
    name: str,
) -> object:
    """
    Import an exported object and store it in its package namespace.

    Parameters
    ----------
    namespace : dict[str, object]
        Global namespace of the package exposing the object.
    exports : dict[str, tuple[str, str]]
        Public names mapped to defining module and attribute names.
    name : str
        Public attribute requested from the package.

    Returns
    -------
    object
        Object exported by its defining module.

    Raises
    ------
    AttributeError
        If the requested name is not part of the package exports.
    """
    target = exports.get(name)
    if target is None:
        message = f"module {namespace['__name__']!r} has no attribute {name!r}"
        raise AttributeError(message)
    module_name, attribute = target
    value = getattr(import_module(module_name), attribute)
    namespace[name] = value
    return value
