from __future__ import annotations
import inspect
from collections.abc import AsyncIterable, AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from functools import lru_cache
from types import FunctionType, MappingProxyType, UnionType
from typing import (
    Annotated, Any, Literal, Union, cast, get_args, get_origin, get_type_hints,
)
from uuid import UUID
import msgspec
from orionis.container.entities.invocation import warm_controller_plan
from orionis.introspection.callables.reflection import ReflectionCallable
from orionis.realtime.decorators import REMOTE_ATTRIBUTE, validate_remote_name
from orionis.realtime.errors import RPCError
from orionis.realtime.hub import Hub
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.rules_executor import _build_plan, _collect_with_plan
from orionis.schemas.schema import Schema as OrionisSchema

_EMPTY = inspect.Parameter.empty
_INVALID_ARGUMENTS = "invalid_arguments"
_VALIDATION_ERROR = "validation_error"
_ARGUMENTS_MESSAGE = "Invalid arguments"
_SCALARS = frozenset({
    str, int, float, bool, bytes, object, type(None), datetime, date, time,
    timedelta, Decimal, UUID, Any,
})
_COLLECTIONS = frozenset({list, tuple, dict, set, frozenset, Sequence, Mapping})

def _base_annotation(annotation: object) -> object:
    """
    Remove metadata wrappers when classifying trusted annotations.

    Parameters
    ----------
    annotation : object
        Resolved developer-owned annotation.

    Returns
    -------
    object
        Underlying annotation, preserving optionality and container parameters.
    """
    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    return annotation

def _is_data(annotation: object) -> bool:
    """
    Identify types whose values may safely originate in decoded client data.

    Parameters
    ----------
    annotation : object
        Resolved callable annotation.

    Returns
    -------
    bool
        Whether the type is a scalar, schema, enum or typed data collection.
    """
    annotation = _base_annotation(annotation)
    origin = get_origin(annotation)
    if origin in {Union, UnionType}:
        return all(_is_data(item) for item in get_args(annotation))
    if origin is Literal:
        return True
    if origin in _COLLECTIONS:
        return all(item is Ellipsis or _is_data(item) for item in get_args(annotation))
    return annotation in _SCALARS or annotation in _COLLECTIONS or (
        isinstance(annotation, type) and issubclass(annotation, (msgspec.Struct, Enum))
    )

def _dependency_type(annotation: object) -> type | None:
    """
    Extract a container-owned service type, including nullable dependencies.

    Parameters
    ----------
    annotation : object
        Resolved trusted annotation.

    Returns
    -------
    type | None
        Concrete or abstract service type, or None for client data/unsupported hints.
    """
    annotation = _base_annotation(annotation)
    if get_origin(annotation) in {Union, UnionType}:
        alternatives = tuple(
            item for item in get_args(annotation) if item is not type(None)
        )
        if len(alternatives) != 1:
            return None
        annotation = _base_annotation(alternatives[0])
    if isinstance(annotation, type) and not _is_data(annotation):
        return annotation
    return None

@dataclass(frozen=True, slots=True)
class _SchemaPlan:
    """Retain trusted field names and existing rule metadata for one Struct."""

    fields: tuple[str, ...]
    rules: tuple

def _schema_plans(annotation: object) -> Mapping[type, _SchemaPlan]: # NOSONAR
    """
    Compile schema traversal and local rules through nested data structures.

    Parameters
    ----------
    annotation : object
        Accepted client annotation, possibly optional or Annotated.

    Returns
    -------
    Mapping[type, _SchemaPlan]
        Immutable traversal metadata, including recursive Struct references.
    """
    plans: dict[type, _SchemaPlan] = {}

    def visit(hint: object) -> None:
        """
        Visit each trusted Struct annotation at most once.

        Parameters
        ----------
        hint : object
            Field or parameter annotation originating in application code.

        Returns
        -------
        None
            Add complete field traversal and rule metadata to the local map.
        """
        hint = _base_annotation(hint)
        if get_origin(hint) in {Union, UnionType} | _COLLECTIONS:
            for item in get_args(hint):
                visit(item)
        elif isinstance(hint, type) and issubclass(hint, msgspec.Struct):
            if hint in plans:
                return
            # Publish before following fields so recursive schemas terminate.
            plans[hint] = _SchemaPlan((), ())
            fields = msgspec.structs.fields(hint)
            for field in fields:
                visit(field.type)
            rules = ()
            if issubclass(hint, OrionisSchema):
                # Traverse nested values ourselves, including collections and
                # plain Struct wrappers, while running each framework rule once.
                rules = tuple(
                    (name, prefix, getter, validators, False)
                    for name, prefix, getter, validators, _nested in _build_plan(hint)
                    if validators
                )
            plans[hint] = _SchemaPlan(tuple(field.name for field in fields), rules)

    visit(annotation)
    return MappingProxyType(plans)

def _validate_schemas( # NOSONAR
    value: object,
    plans: Mapping[type, _SchemaPlan],
) -> None:
    """
    Run existing schema rules across an already converted RPC data value.

    Parameters
    ----------
    value : object
        Converted schema or collection with a compiled schema-containing type.
    plans : Mapping[type, _SchemaPlan]
        Trusted field and rule metadata compiled during Hub registration.

    Returns
    -------
    None
        Execute validation without re-inspecting callable metadata.

    Raises
    ------
    ValidationException
        If a contained schema violates a framework rule.
    """
    if isinstance(value, msgspec.Struct):
        plan = plans.get(type(value))
        if plan is not None:
            if plan.rules:
                failures = []
                _collect_with_plan(plan.rules, value, "", failures)
                if failures:
                    raise ValidationException(failures)
            for name in plan.fields:
                _validate_schemas(getattr(value, name), plans)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            _validate_schemas(item, plans)
    elif isinstance(value, dict):
        for key, item in value.items():
            _validate_schemas(key, plans)
            _validate_schemas(item, plans)

@dataclass(frozen=True, slots=True)
class _ClientParameter:
    """Retain the immutable conversion plan for one client-owned parameter."""

    name: str
    annotation: object
    default: object
    keyword_only: bool
    schema_plans: Mapping[type, _SchemaPlan]

    def convert(self, value: object) -> object:
        """
        Convert one RPC value without accessing an HTTP request body.

        Parameters
        ----------
        value : object
            Explicit client value or trusted declared default.

        Returns
        -------
        object
            Validated scalar, collection, enum or schema.

        Raises
        ------
        RPCError
            If type constraints or schema rules reject the value.
        """
        try:
            converted = msgspec.convert(value, type=cast("type", self.annotation))
            if self.schema_plans:
                _validate_schemas(converted, self.schema_plans)
            return converted
        except (msgspec.ValidationError, ValidationException, TypeError) as exc:
            raise RPCError(_VALIDATION_ERROR, _ARGUMENTS_MESSAGE) from exc

@dataclass(frozen=True, slots=True)
class RemoteMethod:
    """Describe one pre-authorized method without retaining a Hub instance."""

    method_name: str
    is_stream: bool
    dependencies: Mapping[str, type]
    parameters: tuple[_ClientParameter, ...]
    positional: tuple[_ClientParameter, ...]
    client_names: frozenset[str]

    def bind(self, args: list[object], kwargs: dict[str, object]) -> dict[str, object]:
        """
        Bind only client-owned parameters and provide all declared defaults.

        Parameters
        ----------
        args : list[object]
            Positional RPC values, excluding every dependency-injected parameter.
        kwargs : dict[str, object]
            Named RPC values, restricted to the compiled client parameter set.

        Returns
        -------
        dict[str, object]
            Converted client arguments; container dependencies are never included.

        Raises
        ------
        RPCError
            If an argument is missing, duplicated, unknown or invalid.
        """
        if (
            not isinstance(args, list) or not isinstance(kwargs, dict)
            or len(args) > len(self.positional)
            or kwargs.keys() - self.client_names
        ):
            raise RPCError(_INVALID_ARGUMENTS, _ARGUMENTS_MESSAGE)
        provided = {
            parameter.name: value
            for parameter, value in zip(self.positional, args, strict=False)
        }
        if provided.keys() & kwargs.keys():
            raise RPCError(_INVALID_ARGUMENTS, _ARGUMENTS_MESSAGE)
        provided.update(kwargs)
        result = {}
        for parameter in self.parameters:
            value = provided.get(parameter.name, parameter.default)
            if value is _EMPTY:
                raise RPCError(_INVALID_ARGUMENTS, _ARGUMENTS_MESSAGE)
            result[parameter.name] = parameter.convert(value)
        return result

def _method_plan(hub: type[Hub], name: str, function: FunctionType) -> RemoteMethod:
    """
    Compile trusted reflection metadata once, rejecting ambiguous signatures.

    Parameters
    ----------
    hub : type[Hub]
        Registered hub class.
    name : str
        Server-owned Python method name.
    function : FunctionType
        Original decorated function.

    Returns
    -------
    RemoteMethod
        Complete safe binding and dispatch plan.

    Raises
    ------
    TypeError
        If annotations cannot be resolved or a signature is unsupported.
    """
    signature = ReflectionCallable(function).getSignature()
    namespace = dict(vars(hub))
    namespace[hub.__name__] = hub
    try:
        hints = get_type_hints(function, localns=namespace, include_extras=True)
    except (AttributeError, NameError, SyntaxError, TypeError) as exc:
        message = (
            f"Remote annotations must resolve at registration: {hub.__name__}.{name}"
        )
        raise TypeError(message) from exc
    parameters = tuple(signature.parameters.values())
    if not parameters or parameters[0].name != "self":
        message = "Remote methods must declare an instance receiver named self"
        raise TypeError(message)
    clients = []
    dependencies = {}
    for parameter in parameters[1:]:
        if parameter.kind in {
            inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            message = "Remote methods reject positional-only or variadic parameters"
            raise TypeError(message)
        annotation = hints.get(parameter.name, _EMPTY)
        if annotation is _EMPTY:
            message = "Remote parameters require explicit resolvable annotations"
            raise TypeError(message)
        if _is_data(annotation):
            # Validate msgspec support at registration rather than per invocation.
            msgspec.json.Decoder(type=cast("type", annotation))
            clients.append(_ClientParameter(
                parameter.name, annotation, parameter.default,
                parameter.kind is inspect.Parameter.KEYWORD_ONLY,
                _schema_plans(annotation),
            ))
        elif (dependency := _dependency_type(annotation)) is not None:
            dependencies[parameter.name] = dependency
        else:
            message = "Remote parameter annotations cannot mix service and client types"
            raise TypeError(message)
    warm_controller_plan(hub, name)
    return_annotation = hints.get("return")
    origin = get_origin(return_annotation) or return_annotation
    stream = inspect.isasyncgenfunction(function) or origin in {
        AsyncIterable, AsyncIterator,
    }
    return RemoteMethod(
        method_name=name,
        is_stream=stream,
        dependencies=MappingProxyType(dependencies),
        parameters=tuple(clients),
        positional=tuple(
            parameter for parameter in clients if not parameter.keyword_only
        ),
        client_names=frozenset(parameter.name for parameter in clients),
    )

@lru_cache(maxsize=1024)
def compile_hub(hub: type[Hub]) -> Mapping[str, RemoteMethod]:
    """
    Build the immutable remote dispatch map exclusively from class metadata.

    Parameters
    ----------
    hub : type[Hub]
        Developer-owned Hub subclass registered during application boot.

    Returns
    -------
    Mapping[str, RemoteMethod]
        Bounded cached dispatch map; no instance or payload is retained.

    Raises
    ------
    TypeError
        If a remote descriptor, method or annotation is unsupported.
    ValueError
        If aliases conflict or a private method is marked remote.
    """
    if not isinstance(hub, type) or not issubclass(hub, Hub):
        message = "Realtime routes require a Hub subclass"
        raise TypeError(message)
    members: dict[str, object] = {}
    for base in reversed(hub.__mro__):
        members.update(vars(base))
    methods = {}
    for name, descriptor in members.items():
        candidate = (
            descriptor.__func__
            if isinstance(descriptor, (classmethod, staticmethod)) else descriptor
        )
        alias = getattr(candidate, REMOTE_ATTRIBUTE, None)
        if alias is None:
            continue
        if not isinstance(descriptor, FunctionType):
            message = "Remote targets must be ordinary instance methods"
            raise TypeError(message)
        validate_remote_name(name)
        validate_remote_name(alias)
        if alias in methods:
            message = f"Duplicate remote alias: {alias}"
            raise ValueError(message)
        methods[alias] = _method_plan(hub, name, descriptor)
    return MappingProxyType(methods)
