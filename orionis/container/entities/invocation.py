from __future__ import annotations
import inspect
from dataclasses import dataclass
from functools import lru_cache
from types import FunctionType, MethodDescriptorType, MethodType, WrapperDescriptorType
from typing import TYPE_CHECKING, get_type_hints
from orionis.introspection.callables.reflection import ReflectionCallable
from orionis.introspection.concretes.reflection import ReflectionConcrete
from orionis.introspection.dependencies.reflection import (
    _build_dependencies,
    _cached_resolved_signature,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.introspection.dependencies.entities.argument import Argument

@dataclass(frozen=True, slots=True)
class InvocationPlan:
    """
    Describe the immutable metadata needed to invoke one callable.

    Parameters
    ----------
    arguments : tuple[Argument, ...]
        Parameters in declaration order, excluding a bound receiver.
    is_async : bool
        Whether invocation requires awaiting the callable's result.
    """

    arguments: tuple[Argument, ...]
    is_async: bool

@lru_cache(maxsize=1024)
def _callable_plan(target: Callable, *, bound: bool = False) -> InvocationPlan:
    """
    Validate a callable and retain its parameter and coroutine metadata.

    Parameters
    ----------
    target : Callable
        Function underlying the callable.
    bound : bool, optional
        Whether a receiver is supplied by Python's descriptor binding.

    Returns
    -------
    InvocationPlan
        Metadata reusable across different instances of the same controller.
    """
    ReflectionCallable(target)
    signature = _cached_resolved_signature(target, bound=bound)
    return InvocationPlan(
        tuple(signature.ordered.values()), inspect.iscoroutinefunction(target),
    )

def callable_plan(target: Callable) -> InvocationPlan:
    """
    Select a plan using the callable's function and receiver mode.

    Parameters
    ----------
    target : Callable
        Function or bound method invoked by the container.

    Returns
    -------
    InvocationPlan
        Parameter plan that does not retain a bound receiver.
    """
    if isinstance(target, MethodType):
        return _callable_plan(target.__func__, bound=True)
    return _callable_plan(target)

@lru_cache(maxsize=1024)
def constructor_plan(target: type, constructor: object) -> InvocationPlan:
    """
    Validate a concrete class and prepare its constructor metadata.

    Parameters
    ----------
    target : type
        Concrete class instantiated by the container.
    constructor : object
        Current ``__init__`` descriptor, included in the cache identity.

    Returns
    -------
    InvocationPlan
        Shared constructor parameters with resolvable class-local types restored.
    """
    ReflectionConcrete(target)
    signature = _cached_resolved_signature(constructor)
    annotations = getattr(constructor, "__annotations__", {})
    unresolved_names = tuple(
        name
        for name, value in annotations.items()
        if name != "return"
        and isinstance(value, str)
        and (argument := signature.ordered.get(name)) is not None
        and argument.module_name == "typing"
        and argument.type is str
    )
    if not unresolved_names:
        return InvocationPlan(tuple(signature.ordered.values()), is_async=False)

    # Resolve remaining class-local references in the constructor namespace.
    raw_signature = inspect.signature(constructor)
    module = inspect.getmodule(constructor)
    globalns = vars(module) if module is not None else {}
    localns = dict(vars(target))
    localns[target.__name__] = target
    parameters = []
    changed = False
    for parameter in raw_signature.parameters.values():
        hint = parameter.annotation
        updated = parameter
        dependency = signature.ordered.get(parameter.name)
        if (
            isinstance(hint, str)
            and parameter.default is inspect.Parameter.empty
            and dependency is not None
            and dependency.module_name != "typing"
            and isinstance(dependency.type, type)
        ):
            updated = parameter.replace(annotation=dependency.type)
        if parameter.name not in unresolved_names:
            parameters.append(updated)
            continue
        probe = type("_ConstructorHint", (), {
            "__annotations__": {"value": hint},
        })
        try:
            resolved = get_type_hints(
                probe,
                globalns=globalns,
                localns=localns,
            )["value"]
        except (AttributeError, NameError, SyntaxError, TypeError):
            parameters.append(updated)
            continue
        if isinstance(resolved, type):
            updated = parameter.replace(annotation=resolved)
            changed = True
        parameters.append(updated)

    if changed:
        raw_signature = raw_signature.replace(parameters=parameters)
        signature = _build_dependencies(raw_signature)
    return InvocationPlan(tuple(signature.ordered.values()), is_async=False)

def warm_controller_plan(target: type, method_name: str) -> None:
    """
    Prepare ordinary controller descriptors without creating an instance.

    Parameters
    ----------
    target : type
        Controller whose constructor and action will run during requests.
    method_name : str
        Instance, static, or class method selected by the route.

    Returns
    -------
    None
        Standard descriptor plans are cached; custom descriptors remain lazy.

    Notes
    -----
    Static lookup does not execute custom descriptor getters. Only ordinary
    Python functions and built-in constructor descriptors are inspected.
    Dependencies and controller instances are always resolved at request time.
    Plans remain subject to the bounded LRU capacity.
    """
    constructor = inspect.getattr_static(target, "__init__", None)
    if type(constructor) is staticmethod:
        constructor = constructor.__func__
    elif type(constructor) is classmethod:
        constructor = MethodType(constructor.__func__, target)
    if type(constructor) in (
        FunctionType, MethodType, MethodDescriptorType, WrapperDescriptorType,
    ):
        constructor_plan(target, constructor)

    descriptor = inspect.getattr_static(target, method_name, None)
    if type(descriptor) is FunctionType:
        _callable_plan(descriptor, bound=True)
    elif type(descriptor) is staticmethod:
        function = descriptor.__func__
        if type(function) is FunctionType:
            callable_plan(function)
    elif type(descriptor) is classmethod:
        function = descriptor.__func__
        if type(function) is FunctionType:
            _callable_plan(function, bound=True)
