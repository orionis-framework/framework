from __future__ import annotations
from typing import TYPE_CHECKING, Annotated, Union, get_args, get_origin
import operator
import types
import msgspec.structs
from orionis.schemas.rule import Rule
from orionis.schemas.meta.validation import ValidationMetadata

if TYPE_CHECKING:
    from collections.abc import Iterable

# Cache of validation plans for schema types. Keys are schema classes;
# values are tuples of field validation plans as returned by _build_plan().
# Populated on demand by _build_plan and warmed at class creation time.
_PLAN_CACHE: dict[type, tuple] = {}
_ASYNC_PLAN_CACHE: dict[type, tuple | None] = {}

# Alias for faster local access in hot path.
# Avoids global dict lookup on every nested validation call.
_cache_get = _PLAN_CACHE.get
_async_cache_get = _ASYNC_PLAN_CACHE.get

# Shared empty mapping returned for schemas without Orionis metadata.
# Reused instead of allocating a fresh dict on every plan build.
_EMPTY_META: dict[str, list[object]] = {}

def _type_contains_nested(tp: object) -> bool:
    """
    Check whether a type annotation contains a nested Orionis schema.

    Parameters
    ----------
    tp : object
        Type annotation to inspect. May be a plain type or wrapped in
        ``Union``/``|`` or ``Annotated``.

    Returns
    -------
    bool
        Return ``True`` if ``tp`` itself, or any nested/union member, is a
        schema type defining ``__orionis_meta__``; otherwise return ``False``.
    """
    # Fast path for common case: a non-generic schema type.
    origin = get_origin(tp)

    # Unions may contain nested schemas in any member, so check all members.
    if origin is Union or origin is types.UnionType:
        return any(_type_contains_nested(a) for a in get_args(tp))

    # Annotated may wrap a nested schema, but the metadata items it carries are
    if origin is Annotated:
        return _type_contains_nested(get_args(tp)[0])

    # Finally, check if this is a schema type by looking for the marker attribute.
    return isinstance(tp, type) and "__orionis_meta__" in tp.__dict__

def _warm_child_plan(tp: object) -> None:
    """Eagerly populate ``_PLAN_CACHE`` for any nested Orionis schema type.

    Called from ``_build_plan`` so that the first real validation call for a
    nested field always hits the cache instead of triggering a cold build.

    Parameters
    ----------
    tp : object
        Field type annotation, potentially an ``Annotated`` type, ``Union``
        or bare class.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    # Fast path for common case: a non-generic schema type.
    origin = get_origin(tp)

    # Resolve the wrapped type before looking for child schema plans.
    if origin is Annotated:
        _warm_child_plan(get_args(tp)[0])
        return

    # Unions may contain nested schemas in any member, so check all members.
    if origin is Union or origin is types.UnionType:
        for arg in get_args(tp):
            _warm_child_plan(arg)

    # Build a plan for a bare schema type when it has no existing plan.
    elif (
        isinstance(tp, type)
        and "__orionis_meta__" in tp.__dict__
        and _cache_get(tp) is None
    ):
        _build_plan(tp)

def _field_rules(
    klass: type, field_name: str, items: Iterable[object],
) -> tuple[Rule, ...]:
    """
    Select executable rules from a field's validated metadata.

    Parameters
    ----------
    klass : type
        Schema owning the field.
    field_name : str
        Name used in metadata error messages.
    items : Iterable[object]
        Declared rule and documentation metadata.

    Returns
    -------
    tuple[Rule, ...]
        Rules in their declaration order.

    Raises
    ------
    TypeError
        If an item is neither a rule nor supported metadata.
    """
    rules = []
    for item in items:
        if isinstance(item, Rule):
            rules.append(item)
        elif not isinstance(item, ValidationMetadata):
            message = (
                f"Field '{field_name}' on '{klass.__name__}': "
                f"'{type(item).__name__}' is not a valid custom rule. "
                "Custom rules must subclass 'orionis.schemas.rule.Rule'."
            )
            raise TypeError(message)
    return tuple(rules)

def _async_validators(validators: tuple) -> tuple:
    """
    Bind native asynchronous rule overrides once for a validation plan.

    Parameters
    ----------
    validators : tuple
        Synchronous bound Rule.validate methods.

    Returns
    -------
    tuple
        Pairs of bound validators and whether their result must be awaited.
    """
    result = []
    for validate in validators:
        rule = validate.__self__
        asynchronous = type(rule).enforceAsync is not Rule.enforceAsync
        result.append((rule.validateAsync if asynchronous else validate, asynchronous))
    return tuple(result)

def _type_uses_async(field_type: object) -> bool:
    """
    Inspect warmed nested schemas for native asynchronous rules.

    Parameters
    ----------
    field_type : object
        Field annotation, possibly an Annotated type or union.

    Returns
    -------
    bool
        Whether a nested schema requires asynchronous validation.
    """
    origin = get_origin(field_type)
    if origin is Annotated:
        return _type_uses_async(get_args(field_type)[0])
    if origin is Union or origin is types.UnionType:
        return any(_type_uses_async(member) for member in get_args(field_type))
    return isinstance(field_type, type) and bool(_async_cache_get(field_type))

def _build_plan(klass: type) -> tuple:
    """
    Build and cache a validation plan for a schema type.

    Parameters
    ----------
    klass : type
        Schema class whose ``msgspec`` fields and ``__orionis_meta__``
        metadata are inspected.

    Returns
    -------
    tuple
        Cached plan entries as ``(field_name, field_name_dot, getter,
        validators, is_nested)`` tuples. Each entry stores the field name,
        the precomputed dotted field prefix, an ``operator.attrgetter`` for
        field access, the field's bound validator callables, and whether the
        field contains a nested Orionis schema.

    Raises
    ------
    TypeError
        Raised when field metadata contains an object that is neither a
        ``Rule`` instance nor supported validation metadata.
    """
    orionis_meta: dict[str, list[object]] = getattr(
        klass, "__orionis_meta__", _EMPTY_META,
    )
    plan: list = []
    async_plan: list = []
    requires_async = False
    for field in msgspec.structs.fields(klass):
        rules = _field_rules(klass, field.name, orionis_meta.get(field.name, ()))
        is_nested = _type_contains_nested(field.type)
        if rules or is_nested:
            getter = operator.attrgetter(field.name)
            validators = tuple(rule.validate for rule in rules)
            async_validators = _async_validators(validators)
            field_name_dot = field.name + "."
            plan.append((field.name, field_name_dot, getter, validators, is_nested))
            async_plan.append((
                field.name, field_name_dot, getter, async_validators, is_nested,
            ))
            if is_nested:
                _warm_child_plan(field.type)
            requires_async = (
                requires_async
                or any(asynchronous for _, asynchronous in async_validators)
                or _type_uses_async(field.type)
            )
    result = tuple(plan)
    _PLAN_CACHE[klass] = result
    _ASYNC_PLAN_CACHE[klass] = tuple(async_plan) if requires_async else None
    return result

def _collect_nested(
    value: object,
    prefix: str,
    failures: list,
) -> None:
    """
    Validate a nested schema value using its own cached plan.

    Parameters
    ----------
    value : object
        Nested schema instance held by the parent field.
    prefix : str
        Dot-terminated path prefix already qualified with the parent field.
    failures : list
        Accumulator receiving every ``ValidationFailure`` found.

    Returns
    -------
    None
        Return ``None`` after running the nested plan, if any.
    """
    # Resolve the child schema plan, building it only on a cache miss.
    child_klass = type(value)
    child_plan = _cache_get(child_klass)
    if child_plan is None:
        if "__orionis_meta__" not in child_klass.__dict__:
            return
        child_plan = _build_plan(child_klass)

    # Skip schemas that declare neither rules nor further nesting.
    if child_plan:
        _collect_with_plan(child_plan, value, prefix, failures)

def _collect_with_plan(
    plan: tuple,
    instance: object,
    prefix: str,
    failures: list,
) -> None:
    """
    Inner validation loop: execute a pre-resolved plan against an instance.

    This function is the true hot path. It takes the plan as a parameter so
    that callers who already hold it (e.g. ``Schema.validate``) skip the
    cache lookup and the ``type()`` call. Every failure is accumulated so
    the caller can report all of them at once.

    Parameters
    ----------
    plan : tuple
        Non-empty plan produced by ``_build_plan`` for this instance's type.
    instance : object
        Schema instance to validate.
    prefix : str
        Dot-terminated path prefix for nested field names, e.g.
        ``"address."`` so that child fields report ``"address.zip"``.
        Pass ``""`` at the top level.
    failures : list
        Accumulator receiving every ``ValidationFailure`` found.

    Returns
    -------
    None
        Return ``None`` after running every rule in the plan.
    """
    # Bind the accumulator method once instead of resolving it per failure.
    append = failures.append

    # Iterate over each field in the plan, which may have custom
    # rules and/or nested schemas.
    for field_name, field_name_dot, getter, validators, is_nested in plan:

        # Read the current field value from the instance.
        value = getter(instance)

        # Recursively validate the nested object.
        if is_nested and value is not None:
            _collect_nested(value, prefix + field_name_dot, failures)

        # Skip fields that only exist in the plan for nested traversal.
        if not validators:
            continue

        # Build the fully-qualified field path only when a rule needs it.
        qualified = prefix + field_name
        for validate in validators:

            # Run each validator for the current field.
            failure = validate(qualified, value, instance)

            # Keep going so sibling rules and fields are reported too.
            if failure is not None:
                append(failure)

async def _collect_async_rules(
    validators: tuple,
    field: str,
    value: object,
    instance: object,
    failures: list,
) -> None:
    """
    Run preclassified rule callables in declaration order.

    Parameters
    ----------
    validators : tuple
        Pairs of bound validators and their asynchronous flags.
    field : str
        Fully qualified field path.
    value : object
        Converted field value.
    instance : object
        Schema instance or namespace of successfully converted fields.
    failures : list
        Accumulator for validation failures.

    Returns
    -------
    None
        Every rule result has been collected without parallel database access.
    """
    for validate, asynchronous in validators:
        failure = (
            await validate(field, value, instance)
            if asynchronous else validate(field, value, instance)
        )
        if failure is not None:
            failures.append(failure)

async def _collect_async_nested(value: object, prefix: str, failures: list) -> None:
    """
    Validate a nested schema while preserving non-schema union members.

    Parameters
    ----------
    value : object
        Converted nested value.
    prefix : str
        Dot-terminated field path.
    failures : list
        Accumulator for validation failures.

    Returns
    -------
    None
        Nested rules have completed, or the value required no schema traversal.
    """
    child_type = type(value)
    plan = _cache_get(child_type)
    if plan is None:
        if "__orionis_meta__" not in child_type.__dict__:
            return
        plan = _build_plan(child_type)
    async_plan = _async_cache_get(child_type)
    if async_plan:
        await _collect_with_async_plan(async_plan, value, prefix, failures)
    elif plan:
        _collect_with_plan(plan, value, prefix, failures)

async def _collect_with_async_plan(
    plan: tuple, instance: object, prefix: str, failures: list,
) -> None:
    """
    Execute a plan containing native asynchronous rules or nested schemas.

    Parameters
    ----------
    plan : tuple
        Precompiled asynchronous field plan.
    instance : object
        Converted schema instance.
    prefix : str
        Dot-terminated prefix for nested paths.
    failures : list
        Accumulator for all failures in declaration order.

    Returns
    -------
    None
        Synchronous and asynchronous rule results have been collected.
    """
    for field, field_dot, getter, validators, nested in plan:
        value = getter(instance)
        if nested and value is not None:
            await _collect_async_nested(value, prefix + field_dot, failures)
        if validators:
            await _collect_async_rules(
                validators, prefix + field, value, instance, failures,
            )
