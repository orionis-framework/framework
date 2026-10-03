from __future__ import annotations
import functools
import inspect
from types import MethodType
from typing import Any, get_type_hints
import msgspec
from orionis.introspection.dependencies.contracts.reflection import (
    IReflectDependencies,
)
from orionis.introspection.dependencies.entities.argument import Argument
from orionis.introspection.dependencies.entities.signature import (
    Signature,
)

_SKIP_NAMES: frozenset[str] = frozenset({"self", "cls"})
_SKIP_KINDS: frozenset[int] = frozenset({
    inspect.Parameter.VAR_POSITIONAL,
    inspect.Parameter.VAR_KEYWORD,
})
_KEYWORD_ONLY: int          = inspect.Parameter.KEYWORD_ONLY
_PARAM_EMPTY                = inspect.Parameter.empty
_ANY_TYPE: type             = type(Any)
_ANY_MODULE: str            = _ANY_TYPE.__module__
_ANY_NAME: str              = _ANY_TYPE.__name__
_ANY_FULL_PATH: str         = f"{_ANY_MODULE}.{_ANY_NAME}"
_STRUCT_TYPE: type          = msgspec.Struct

@functools.lru_cache(maxsize=1024)
def _get_signature(target: Any) -> inspect.Signature:
    """
    Return the cached inspect signature for a target.

    Parameters
    ----------
    target : Any
        Callable, method, function, or class to inspect.

    Returns
    -------
    inspect.Signature
        Cached signature object for the provided target.
    """
    return inspect.signature(target)

def _resolve_parameter_hint(
    annotation: str,
    globalns: dict[str, Any],
) -> object:
    """
    Resolve one string hint independently of other unavailable references.

    Parameters
    ----------
    annotation : str
        Parameter annotation requiring evaluation.
    globalns : dict[str, Any]
        Namespace of the callable's defining module.

    Returns
    -------
    object
        Resolved annotation, or None if the reference cannot be evaluated.
    """
    probe = type("_ParameterHint", (), {"__annotations__": {"value": annotation}})
    try:
        return get_type_hints(probe, globalns=globalns)["value"]
    except (AttributeError, NameError, SyntaxError, TypeError):
        return None

def _resolve_future_annotations(
    target: Any,
    signature: inspect.Signature,
) -> inspect.Signature:
    """
    Resolve available string annotations in a callable signature.

    Parameters
    ----------
    target : Any
        Callable declaring the annotations.
    signature : inspect.Signature
        Signature whose parameters may contain string annotations.

    Returns
    -------
    inspect.Signature
        Signature with available types substituted and defaults preserved.
    """
    parameters = tuple(signature.parameters.values())
    if not any(
        isinstance(parameter.annotation, str)
        and parameter.default is _PARAM_EMPTY
        for parameter in parameters
    ):
        return signature

    module = inspect.getmodule(target)
    globalns = vars(module) if module is not None else {}
    try:
        hints = get_type_hints(target, globalns=globalns)
    except (AttributeError, NameError, SyntaxError, TypeError):
        hints = None

    changed = False
    updated_parameters = []
    for parameter in parameters:
        hint = parameter.annotation
        if not isinstance(hint, str) or parameter.default is not _PARAM_EMPTY:
            updated_parameters.append(parameter)
            continue
        if hints is None:
            resolved = _resolve_parameter_hint(hint, globalns)
        else:
            resolved = hints.get(parameter.name)
        if isinstance(resolved, type):
            updated = parameter.replace(annotation=resolved)
            changed = True
        else:
            updated = parameter
        updated_parameters.append(updated)
    if changed:
        return signature.replace(parameters=updated_parameters)
    return signature

def _resolve_annotation(annotation: Any) -> tuple[str, str, Any]:
    """
    Resolve a parameter annotation into its module, name, and type components.

    Parameters
    ----------
    annotation : Any
        The annotation object from an ``inspect.Parameter``. May be a string
        (forward reference) or an actual type/class.

    Returns
    -------
    tuple[str, str, Any]
        A three-element tuple ``(module_name, class_name, type_or_annotation)``
        where ``module_name`` and ``class_name`` identify the annotation's
        origin, and ``type_or_annotation`` is the resolved type (or ``str``
        for forward references).
    """
    # Forward references (string annotations) fall back to the typing module.
    if isinstance(annotation, str):
        return "typing", annotation, str
    ann_module = getattr(annotation, "__module__", "typing")
    ann_name   = getattr(annotation, "__name__", str(annotation))
    return ann_module, ann_name, annotation

def _build_dependencies(signature: inspect.Signature) -> Signature:  # NOSONAR
    """
    Categorize signature parameters as resolved or unresolved dependencies.

    Parameters
    ----------
    signature : inspect.Signature
        The signature object to analyze.

    Returns
    -------
    Signature
        An object containing categorized resolved and unresolved
        parameter dependencies.
    """
    # Accumulation buckets for the three dependency categories.
    resolved_args: dict[str, Argument] = {}
    unresolved_args: dict[str, Argument] = {}
    ordered: dict[str, Argument] = {}

    for param_name, param in signature.parameters.items():

        # Skip irrelevant parameters (self, cls, *args, **kwargs).
        if param_name in _SKIP_NAMES or param.kind in _SKIP_KINDS:
            continue

        is_keyword_only = param.kind == _KEYWORD_ONLY
        annotation = param.annotation
        default    = param.default
        empty      = param.empty

        # No annotation and no default → unresolved.
        if annotation is empty and default is empty:
            arg = Argument(
                name=param_name,
                resolved=False,
                module_name=_ANY_MODULE,
                class_name=_ANY_NAME,
                type=_ANY_TYPE,
                full_class_path=_ANY_FULL_PATH,
                is_keyword_only=is_keyword_only,
            )
            unresolved_args[param_name] = arg
            ordered[param_name] = arg
            continue

        # Has a default value → resolved (type info comes from the default).
        if default is not empty:
            default_type = type(default)
            dt_module    = default_type.__module__
            dt_name      = default_type.__name__
            arg = Argument(
                name=param_name,
                resolved=True,
                module_name=dt_module,
                class_name=dt_name,
                type=default_type,
                full_class_path=dt_module + "." + dt_name,
                is_keyword_only=is_keyword_only,
                default=default,
            )
            resolved_args[param_name] = arg
            ordered[param_name] = arg
            continue

        # Describe the type declared by an annotated parameter.
        ann_module, ann_name, ann_type = _resolve_annotation(annotation)
        is_str_ann = isinstance(annotation, str)

        # Builtin type without a default → unresolved.
        if ann_module == "builtins":
            arg = Argument(
                name=param_name,
                resolved=False,
                module_name=ann_module,
                class_name=ann_name,
                type=ann_type,
                is_keyword_only=is_keyword_only,
                full_class_path=ann_module + "." + ann_name,
            )
            unresolved_args[param_name] = arg
            ordered[param_name] = arg
        else:
            # Non-builtin annotated type → resolved; detect msgspec schemas.
            is_schema = (
                not is_str_ann
                and isinstance(annotation, type)
                and issubclass(annotation, _STRUCT_TYPE)
            )
            arg = Argument(
                name=param_name,
                resolved=True,
                module_name=ann_module,
                class_name=ann_name,
                type=ann_type,
                is_keyword_only=is_keyword_only,
                is_schema=is_schema,
                full_class_path=ann_module + "." + ann_name,
                default=_PARAM_EMPTY,
            )
            resolved_args[param_name] = arg
            ordered[param_name] = arg

    return Signature(
        resolved=resolved_args,
        unresolved=unresolved_args,
        ordered=ordered,
    )

@functools.lru_cache(maxsize=1024)
def _cached_resolved_signature(target: Any, *, bound: bool = False) -> Signature:
    """
    Return the cached dependency signature for ``target``.

    Parameters
    ----------
    target : Any
        Object whose inspectable signature is resolved into dependencies.
    bound : bool, optional
        Whether the first positional parameter is supplied by method binding.

    Returns
    -------
    Signature
        Dependency signature built from the target's inspectable signature.

    Raises
    ------
    ValueError
        Raised when the target signature cannot be inspected.

    Notes
    -----
    Cached exceptions are not stored by ``functools.lru_cache``, so failures
    are raised again on subsequent calls.
    """
    try:
        sig = _get_signature(target)
        if bound:
            parameters = tuple(sig.parameters.values())
            if not parameters or parameters[0].kind in (
                inspect.Parameter.KEYWORD_ONLY,
                inspect.Parameter.VAR_KEYWORD,
            ):
                message = "Invalid signature for a bound method."
                raise ValueError(message)
            if parameters[0].kind is not inspect.Parameter.VAR_POSITIONAL:
                sig = sig.replace(parameters=parameters[1:])
    except (ValueError, TypeError) as e:
        error_msg = f"Unable to inspect signature of {target}: {e!s}"
        raise ValueError(error_msg) from e
    return _build_dependencies(_resolve_future_annotations(target, sig))

def _get_resolved_signature(target: Any) -> Signature:
    """
    Return dependency metadata without caching a bound method's receiver.

    Parameters
    ----------
    target : Any
        Callable whose parameters are inspected.

    Returns
    -------
    Signature
        Shared metadata keyed by the underlying function and binding mode.
    """
    if isinstance(target, MethodType):
        return _cached_resolved_signature(target.__func__, bound=True)
    return _cached_resolved_signature(target)


_get_resolved_signature.cache_clear = _cached_resolved_signature.cache_clear
_get_resolved_signature.cache_info = _cached_resolved_signature.cache_info

class ReflectDependencies(IReflectDependencies):
    """
    Reflect dependency metadata from callables, constructors, and methods.

    Wraps the module-level LRU-cached resolution functions behind a
    stateful, contract-bound interface, preserving zero overhead on
    repeated inspections of the same target.
    """

    # ruff: noqa: ANN401

    __slots__ = ("_target",)

    def __init__(self, target: Any | None = None) -> None:
        """
        Initialize the ReflectDependencies instance.

        Parameters
        ----------
        target : Any | None, optional
            The object whose dependencies are to be reflected.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Store the target for subsequent reflection calls.
        self._target = target

    def constructorSignature(self) -> Signature:
        """
        Inspect the constructor (__init__) and categorize parameter dependencies.

        Returns
        -------
        Signature
            Contains resolved and unresolved parameter dependencies.

        Raises
        ------
        ValueError
            If the constructor signature cannot be inspected.
        """
        # Delegate to the cached resolver using the bound __init__ method.
        return _get_resolved_signature(self._target.__init__)

    def methodSignature(self, method_name: str) -> Signature:
        """
        Inspect a named method and categorize its parameter dependencies.

        Parameters
        ----------
        method_name : str
            Name of the method to inspect.

        Returns
        -------
        Signature
            Categorized resolved and unresolved parameter dependencies.

        Raises
        ------
        ValueError
            If the method does not exist or its signature cannot be inspected.
        """
        # Retrieve the bound method by name then resolve its dependencies.
        return _get_resolved_signature(getattr(self._target, method_name))

    def callableSignature(self) -> Signature:
        """
        Inspect the callable target and categorize its parameter dependencies.

        Returns
        -------
        Signature
            Contains resolved and unresolved parameter dependencies.

        Raises
        ------
        TypeError
            If the target is not callable.
        ValueError
            If the target's signature cannot be inspected.
        """
        # Guard against non-callable targets before attempting introspection.
        if not callable(self._target):
            error_msg = (
                f"Target {self._target} is not callable and cannot have a signature."
            )
            raise TypeError(error_msg)
        return _get_resolved_signature(self._target)
