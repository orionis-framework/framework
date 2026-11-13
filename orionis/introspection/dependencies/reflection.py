# ruff: noqa: TC003
# Dependency annotations are dynamic; callbacks remain runtime inspectable.
"""Reflect dependency metadata from callables, constructors, and methods."""

from __future__ import annotations
import functools
import inspect
from annotationlib import Format, ForwardRef, get_annotations
from collections.abc import Callable
from types import FunctionType, MethodDescriptorType, MethodType, WrapperDescriptorType
from typing import Any, get_type_hints
import msgspec
from orionis.introspection.dependencies.contracts.reflection import (
    IReflectDependencies,
)
from orionis.introspection.dependencies.entities.argument import Argument
from orionis.introspection.dependencies.entities.signature import (
    Signature,
)

_SKIP_KINDS: frozenset[int] = frozenset(
    {
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.VAR_KEYWORD,
    },
)
"""Skip kinds used by ``reflection``."""
_KEYWORD_ONLY: int = inspect.Parameter.KEYWORD_ONLY
_PARAM_EMPTY = inspect.Parameter.empty
_ANY_TYPE: type = type(Any)
"""Any type used by ``reflection``."""
_ANY_MODULE: str = _ANY_TYPE.__module__
_ANY_NAME: str = _ANY_TYPE.__name__
_ANY_FULL_PATH: str = f"{_ANY_MODULE}.{_ANY_NAME}"
"""Any full path used by ``reflection``."""
_STRUCT_TYPE: type = msgspec.Struct

_signature_invalidators: dict[str, Callable[[], None]] = {}
"""Dependent cache clearers keyed by stable consumer identifiers."""


def _register_signature_invalidator(key: str, callback: Callable[[], None]) -> None:
    """Register one dependent cache clearer without retaining reloaded callbacks.

    Parameters
    ----------
    key : str
        Stable identifier of the internal cache consumer.
    callback : collections.abc.Callable[[], None]
        Function clearing that consumer's derived metadata.

    Returns
    -------
    None
        No return value.
    """
    _signature_invalidators[key] = callback


def _clear_dependency_caches() -> None:
    """Invalidate shared signatures and registered derived metadata explicitly.

    Returns
    -------
    None
        No return value.
    """
    _get_signature.cache_clear()
    _cached_resolved_signature.cache_clear()
    for callback in tuple(_signature_invalidators.values()):
        callback()


def _inspect_annotations(target: object) -> dict[str, object]:
    """Read annotations while preserving unknown native deferred references.

    Parameters
    ----------
    target : object
        Class, function, or module declaring annotations.

    Returns
    -------
    dict[str, object]
        Known annotation values and ForwardRef objects for unavailable names.
    """
    try:
        return get_annotations(target)
    except NameError:
        return get_annotations(target, format=Format.FORWARDREF)


def _inspect_signature(target: object) -> inspect.Signature:
    """Inspect a signature while preserving unavailable native annotations.

    Parameters
    ----------
    target : object
        Callable, method, function, or class to inspect.

    Returns
    -------
    inspect.Signature
        Runtime values where available, with ForwardRef values for unknown names.
    """
    try:
        return inspect.signature(target)
    except NameError:
        return inspect.signature(
            target,
            annotation_format=Format.FORWARDREF,  # NOSONAR(S930) - Python 3.14 API.
        )


@functools.lru_cache(maxsize=1024)
def _get_signature(target: object) -> inspect.Signature:
    """
    Return the cached inspect signature for a target.

    Parameters
    ----------
    target : object
        Callable, method, function, or class to inspect.

    Returns
    -------
    ``inspect.Signature``
        Cached signature object for the provided target.
    """
    return _inspect_signature(target)


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
    globalns : dict[str, typing.Any]
        Namespace of the callable's defining module.

    Returns
    -------
    object
        Resolved annotation, or None if the reference cannot be evaluated.
    """
    probe = type("_ParameterHint", (), {"__annotations__": {"value": annotation}})
    try:
        return get_type_hints(probe, globalns=globalns)["value"]
    except AttributeError, NameError, SyntaxError, TypeError:
        return None


def _resolve_future_annotations(
    target: object,
    signature: inspect.Signature,
) -> inspect.Signature:
    """
    Resolve available string annotations in a callable signature.

    Parameters
    ----------
    target : object
        Callable declaring the annotations.
    signature : ``inspect.Signature``
        Signature whose parameters may contain string annotations.

    Returns
    -------
    ``inspect.Signature``
        Signature with available types substituted and defaults preserved.
    """
    parameters = tuple(signature.parameters.values())
    if not any(
        isinstance(parameter.annotation, str) and parameter.default is _PARAM_EMPTY
        for parameter in parameters
    ):
        return signature

    module = inspect.getmodule(target)
    globalns = vars(module) if module is not None else {}
    try:
        hints = get_type_hints(target, globalns=globalns)
    except AttributeError, NameError, SyntaxError, TypeError:
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


def _resolve_annotation(annotation: object) -> tuple[str, str, object]:
    """
    Resolve a parameter annotation into its module, name, and type components.

    Parameters
    ----------
    annotation : object
        The annotation object from an ``inspect.Parameter``. May be a string
        (forward reference) or an actual type/class.

    Returns
    -------
    tuple[str, str, object]
        A three-element tuple ``(module_name, class_name, type_or_annotation)``
        where ``module_name`` and ``class_name`` identify the annotation's
        origin, and ``type_or_annotation`` is the resolved type (or ``str``
        for forward references).
    """
    # Forward references (string annotations) fall back to the typing module.
    if isinstance(annotation, ForwardRef):
        return "typing", annotation.__forward_arg__, str
    if isinstance(annotation, str):
        return "typing", annotation, str
    ann_module = getattr(annotation, "__module__", "typing")
    ann_name = getattr(annotation, "__name__", str(annotation))
    return ann_module, ann_name, annotation


def _parameter_dependency(parameter: inspect.Parameter) -> Argument:
    """Describe one non-variadic parameter using its default or annotation.

    Parameters
    ----------
    parameter : inspect.Parameter
        Explicit parameter whose dependency metadata is required.

    Returns
    -------
    orionis.introspection.dependencies.entities.argument.Argument
        Resolution metadata preserving the parameter's declared name and kind.
    """
    annotation = parameter.annotation
    default = parameter.default
    is_keyword_only = parameter.kind == _KEYWORD_ONLY
    if default is not _PARAM_EMPTY:
        default_type = type(default)
        return Argument(
            name=parameter.name,
            resolved=True,
            module_name=default_type.__module__,
            class_name=default_type.__name__,
            type=default_type,
            full_class_path=f"{default_type.__module__}.{default_type.__name__}",
            is_keyword_only=is_keyword_only,
            default=default,
        )
    if annotation is _PARAM_EMPTY:
        return Argument(
            name=parameter.name,
            resolved=False,
            module_name=_ANY_MODULE,
            class_name=_ANY_NAME,
            type=_ANY_TYPE,
            full_class_path=_ANY_FULL_PATH,
            is_keyword_only=is_keyword_only,
        )
    module, name, annotation_type = _resolve_annotation(annotation)
    resolved = module != "builtins"
    return Argument(
        name=parameter.name,
        resolved=resolved,
        module_name=module,
        class_name=name,
        type=annotation_type,
        full_class_path=f"{module}.{name}",
        is_keyword_only=is_keyword_only,
        is_schema=isinstance(annotation, type) and issubclass(annotation, _STRUCT_TYPE),
        default=_PARAM_EMPTY if resolved else None,
    )


def _build_dependencies(signature: inspect.Signature) -> Signature:
    """Categorize explicit parameters after descriptor binding has been applied.

    Parameters
    ----------
    signature : inspect.Signature
        Signature containing only caller-supplied parameters.

    Returns
    -------
    orionis.introspection.dependencies.entities.signature.Signature
        Resolved and unresolved dependencies in declaration order.
    """
    resolved: dict[str, Argument] = {}
    unresolved: dict[str, Argument] = {}
    ordered: dict[str, Argument] = {}
    for parameter in signature.parameters.values():
        if parameter.kind in _SKIP_KINDS:
            continue
        argument = _parameter_dependency(parameter)
        ordered[parameter.name] = argument
        bucket = resolved if argument.resolved else unresolved
        bucket[parameter.name] = argument
    return Signature(resolved=resolved, unresolved=unresolved, ordered=ordered)


@functools.lru_cache(maxsize=1024)
def _cached_resolved_signature(target: object, *, bound: bool = False) -> Signature:
    """
    Return the cached dependency signature for ``target``.

    Parameters
    ----------
    target : object
        Object whose inspectable signature is resolved into dependencies.
    bound : bool, optional
        Whether the first positional parameter is supplied by method binding.

    Returns
    -------
    orionis.introspection.dependencies.entities.signature.Signature
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


def _get_resolved_signature(target: object) -> Signature:
    """
    Return dependency metadata without caching a bound method's receiver.

    Parameters
    ----------
    target : object
        Callable whose parameters are inspected.

    Returns
    -------
    orionis.introspection.dependencies.entities.signature.Signature
        Shared metadata keyed by the underlying function and binding mode.
    """
    if isinstance(target, MethodType):
        return _cached_resolved_signature(target.__func__, bound=True)
    if not isinstance(target, FunctionType):
        try:
            hash(target)
        except TypeError:
            try:
                signature = _inspect_signature(target)
            except (TypeError, ValueError) as error:
                message = f"Unable to inspect signature of {target}: {error!s}"
                raise ValueError(message) from error
            return _build_dependencies(_resolve_future_annotations(target, signature))
    return _cached_resolved_signature(target)


_get_resolved_signature.cache_clear = _cached_resolved_signature.cache_clear
_get_resolved_signature.cache_info = _cached_resolved_signature.cache_info


class ReflectDependencies(IReflectDependencies):
    """
    Reflect dependency metadata from callables, constructors, and methods.

    Wraps the module-level LRU-cached resolution functions behind a
    stateful, contract-bound interface, reusing bounded metadata caches across
    repeated inspections of the same target.
    """

    __slots__ = ("_target",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, target: object | None = None) -> None:
        """
        Initialize the ReflectDependencies instance.

        Parameters
        ----------
        target : object | None, optional
            The object whose dependencies are to be reflected.

        Returns
        -------
        None
            No return value.
        """
        # Store the target for subsequent reflection calls.
        self._target = target
        """The object whose dependencies are to be reflected."""

    def constructorSignature(self) -> Signature:
        """
        Inspect the constructor (__init__) and categorize parameter dependencies.

        Returns
        -------
        orionis.introspection.dependencies.entities.signature.Signature
            Contains resolved and unresolved parameter dependencies.

        Raises
        ------
        ValueError
            If the constructor signature cannot be inspected.
        """
        return self.methodSignature("__init__")

    def methodSignature(self, method_name: str) -> Signature:
        """
        Inspect a named method and categorize its parameter dependencies.

        Parameters
        ----------
        method_name : str
            Name of the method to inspect.

        Returns
        -------
        orionis.introspection.dependencies.entities.signature.Signature
            Categorized resolved and unresolved parameter dependencies.

        Raises
        ------
        AttributeError
            If the target has no method with the requested name.
        ValueError
            If the method's signature cannot be inspected.
        """
        method = getattr(self._target, method_name)
        if isinstance(self._target, type):
            descriptor = inspect.getattr_static(self._target, method_name)
            if isinstance(
                descriptor,
                (FunctionType, MethodDescriptorType, WrapperDescriptorType),
            ):
                return _cached_resolved_signature(method, bound=True)
        return _get_resolved_signature(method)

    def callableSignature(self) -> Signature:
        """
        Inspect the callable target and categorize its parameter dependencies.

        Returns
        -------
        orionis.introspection.dependencies.entities.signature.Signature
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
