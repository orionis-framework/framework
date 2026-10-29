from __future__ import annotations
from collections.abc import Collection, Mapping
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

# Alias for faster local access in hot path.
# Avoids global dict lookup on every nested validation call.
_cache_get = _PLAN_CACHE.get

# Shared empty mapping returned for schemas without Orionis metadata.
# Reused instead of allocating a fresh dict on every plan build.
_EMPTY_META: dict[str, list[object]] = {}

def _type_contains_nested(tp: object, *, rules_only: bool = False) -> bool:
    """
    Check an annotation for nested schemas requiring traversal.

    Parameters
    ----------
    tp : object
        Type annotation to inspect. May be a plain type or wrapped in
        ``Union``/``|``, ``Annotated`` or a collection.
    rules_only : bool, optional
        Exclude child schemas with an empty cached rule plan when ``True``.

    Returns
    -------
    bool
        Whether a direct, collection or union member is an Orionis schema
        satisfying the ``rules_only`` filter.
    """
    # Fast path for common case: a non-generic schema type.
    origin = get_origin(tp)

    # Unions may contain nested schemas in any member, so check all members.
    if origin is Union or origin is types.UnionType:
        return any(
            _type_contains_nested(a, rules_only=rules_only) for a in get_args(tp)
        )

    # Annotated may wrap a nested schema, but the metadata items it carries are
    if origin is Annotated:
        return _type_contains_nested(get_args(tp)[0], rules_only=rules_only)

    if isinstance(origin, type) and issubclass(origin, Collection):
        args = get_args(tp)
        if issubclass(origin, Mapping):
            args = args[1:]
        return any(
            _type_contains_nested(arg, rules_only=rules_only) for arg in args
        )

    # Finally, check if this is a schema type by looking for the marker attribute.
    return (
        isinstance(tp, type) and "__orionis_meta__" in tp.__dict__
        and (not rules_only or _cache_get(tp) != ())
    )

def _warm_child_plan(tp: object) -> None:
    """Eagerly populate ``_PLAN_CACHE`` for any nested Orionis schema type.

    Called from ``_build_plan`` so that the first real validation call for a
    nested field always hits the cache instead of triggering a cold build.

    Parameters
    ----------
    tp : object
        Field type annotation, potentially an ``Annotated`` type, ``Union``
        or collection, or a bare class.

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

    elif isinstance(origin, type) and issubclass(origin, Collection):
        args = get_args(tp)
        if issubclass(origin, Mapping):
            args = args[1:]
        for arg in args:
            _warm_child_plan(arg)

    # Build a plan for a bare schema type when it has no existing plan.
    elif (
        isinstance(tp, type)
        and "__orionis_meta__" in tp.__dict__
        and _cache_get(tp) is None
    ):
        _build_plan(tp)

def _collection_item_type(tp: object, selector: str) -> object | None:
    """
    Resolve the element annotation selected from a concrete collection type.

    Parameters
    ----------
    tp : object
        Unwrapped collection annotation.
    selector : str
        Sequence index or dictionary key.

    Returns
    -------
    object | None
        Element annotation, or ``None`` for an incompatible selector.
    """
    origin = get_origin(tp)
    args = get_args(tp)
    if not args:
        return None
    if isinstance(origin, type) and issubclass(origin, Mapping):
        return args[1]
    if origin is tuple and args[-1] is not Ellipsis:
        if selector.isdecimal() and int(selector) < len(args):
            return args[int(selector)]
        return None
    if isinstance(origin, type) and issubclass(origin, Collection):
        return args[0]
    return None

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

def _build_plan(klass: type) -> tuple:
    """
    Build and cache the custom-rule execution plan for a schema.

    Parameters
    ----------
    klass : type
        Schema class whose ``msgspec`` fields and ``__orionis_meta__``
        metadata are inspected.

    Returns
    -------
    tuple
        Entries of ``(encoded_name, dotted_prefix, getter, validators,
        is_nested)``. Omit fields and descendants with no custom rules.

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
    nested_types: list[object] = []
    for field in msgspec.structs.fields(klass):
        rules = _field_rules(klass, field.name, orionis_meta.get(field.name, ()))
        # Native conversion has already validated these children. Do not walk
        # them again in Python when no descendant has a custom rule to run.
        is_nested = _type_contains_nested(field.type, rules_only=True)
        if rules or is_nested:
            getter = operator.attrgetter(field.name)
            validators = tuple(rule.validate for rule in rules)
            field_name_dot = field.encode_name + "."
            plan.append((
                field.encode_name, field_name_dot, getter, validators, is_nested,
            ))
            if is_nested:
                nested_types.append(field.type)
    result = tuple(plan)
    _PLAN_CACHE[klass] = result
    for field_type in nested_types:
        _warm_child_plan(field_type)
    return result

async def _collect_nested(
    value: object,
    prefix: str,
    failures: list,
) -> None:
    """
    Validate nested schemas, including schemas held inside collections.

    Parameters
    ----------
    value : object
        Nested schema or collection held by the parent field.
    prefix : str
        Dot-terminated path prefix already qualified with the parent field.
    failures : list
        Accumulator receiving every ``ValidationFailure`` found.

    Returns
    -------
    None
        Return ``None`` after running the nested plan, if any.
    """
    if isinstance(value, Mapping):
        base = prefix[:-1]
        for key, item in value.items():
            await _collect_nested(item, f"{base}[{key!r}].", failures)
        return

    if isinstance(value, list | tuple | set | frozenset):
        base = prefix[:-1]
        for index, item in enumerate(value):
            await _collect_nested(item, f"{base}[{index}].", failures)
        return

    # Resolve the child schema plan, building it only on a cache miss.
    child_klass = type(value)
    child_plan = _cache_get(child_klass)
    if child_plan is None:
        if "__orionis_meta__" not in child_klass.__dict__:
            return
        child_plan = _build_plan(child_klass)

    # Skip schemas that declare neither rules nor further nesting.
    if child_plan:
        await _collect_with_plan(child_plan, value, prefix, failures)

async def _collect_with_plan(
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
            await _collect_nested(value, prefix + field_name_dot, failures)

        # Skip fields that only exist in the plan for nested traversal.
        if not validators:
            continue

        # Build the fully-qualified field path only when a rule needs it.
        qualified = prefix + field_name
        for validate in validators:

            # Run each validator for the current field.
            failure = await validate(qualified, value, instance)

            # Keep going so sibling rules and fields are reported too.
            if failure is not None:
                append(failure)
