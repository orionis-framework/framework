from __future__ import annotations
from typing import Annotated, Union, get_args, get_origin
import operator
import types
import msgspec.structs
from orionis.schemas.rule import Rule
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.meta.validation import ValidationMetadata

# Cache of validation plans for schema types. Keys are schema classes;
# values are tuples of field validation plans as returned by _build_plan().
# Populated on demand by _execute and _build
_PLAN_CACHE: dict[type, tuple] = {}

# Alias for faster local access in hot path.
# Avoids global dict lookup on every nested validation call.
_cache_get = _PLAN_CACHE.get

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
    """
    Eagerly populate ``_PLAN_CACHE`` for any nested Orionis schema type.

    Called from ``_build_plan`` so that the first real validation call for a
    nested field always hits the cache instead of triggering a cold build.

    Parameters
    ----------
    tp : object
        Field type annotation, potentially a ``Union`` or bare class.
    """
    # Fast path for common case: a non-generic schema type.
    origin = get_origin(tp)

    # Unions may contain nested schemas in any member, so check all members.
    if origin is Union or origin is types.UnionType:
        for arg in get_args(tp):
            if (
                isinstance(arg, type)
                and "__orionis_meta__" in arg.__dict__
                and _cache_get(arg) is None
            ):
                _build_plan(arg)

    # Annotated may wrap a nested schema, but the metadata items it carries are
    # irrelevant for plan caching, so skip directly to the wrapped type.
    elif (
        isinstance(tp, type)
        and "__orionis_meta__" in tp.__dict__
        and _cache_get(tp) is None
    ):
        _build_plan(tp)


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
    # Read per-field Orionis metadata attached to the schema class.
    orionis_meta: dict[str, list[object]] = getattr(klass, "__orionis_meta__", {})

    # Collect compiled plan entries for fields that require work at runtime.
    plan: list = []

    # Iterate over declared msgspec fields in definition order.
    for f in msgspec.structs.fields(klass):

        # Retrieve validation metadata for the current field.
        field_items = orionis_meta.get(f.name, ())

        # Keep only executable custom rules for this field.
        rules: list[Rule] = []
        for item in field_items:
            if isinstance(item, Rule):
                rules.append(item)
            elif isinstance(item, ValidationMetadata):
                # Ignore non-executable validation metadata entries.
                continue
            else:
                # Fail fast on unsupported metadata objects.
                msg = (
                    f"Field '{f.name}' on '{klass.__name__}': "
                    f"'{type(item).__name__}' is not a valid custom rule. "
                    f"Custom rules must subclass "
                    f"'orionis.schemas.rule.Rule'."
                )
                raise TypeError(msg)

        # Detect whether the field type contains a nested Orionis schema.
        is_nested = _type_contains_nested(f.type)

        # Store only fields that have rule checks or nested-schema traversal.
        if rules or is_nested:

            # Precompile attribute access to reduce per-instance overhead.
            getter = operator.attrgetter(f.name)

            # Pre-bind rule callables for fast execution in the hot path.
            validators = tuple(r.validate for r in rules)

            # Precompute dotted prefix used when building nested paths.
            field_name_dot = f.name + "."
            plan.append((f.name, field_name_dot, getter, validators, is_nested))

            # Warm child schema plans to avoid recursive cache misses later.
            if is_nested:
                _warm_child_plan(f.type)

    # Store the plan as an immutable tuple to
    # avoid accidental mutation and to save memory.
    result = tuple(plan)

    # Cache the plan for this class so that future validations can skip the build step.
    _PLAN_CACHE[klass] = result

    # Return the plan for use in the current validation call.
    return result

def _collect_with_plan(
    plan: tuple,
    instance: object,
    prefix: str,
    failures: list,
) -> None:
    """
    Inner validation loop: execute a pre-resolved plan against an instance.

    This function is the true hot path. It is separated from ``_execute`` so
    that callers who already hold the plan (e.g. ``Schema.validate``) can
    skip the redundant cache lookup and ``type()`` call. Every failure is
    accumulated so the caller can report all of them at once.

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
    # Iterate over each field in the plan, which may have custom
    # rules and/or nested schemas.
    for field_name, field_name_dot, getter, validators, is_nested in plan:

        # Read the current field value from the instance.
        value = getter(instance)

        # Build the fully-qualified field path.
        qualified = prefix + field_name
        if is_nested and value is not None:

            # Resolve the child schema plan for nested validation.
            child_klass = type(value)
            child_plan = _cache_get(child_klass)
            if child_plan is None:
                child_plan = _build_plan(child_klass)
            if child_plan:

                # Recursively validate the nested object.
                _collect_with_plan(
                    child_plan, value, prefix + field_name_dot, failures,
                )

        # Execute each custom rule validator for this field, if any.
        for validate in validators:

            # Run each validator for the current field.
            failure = validate(qualified, value, instance)
            if failure is not None:

                # Keep going so sibling rules and fields are reported too.
                failures.append(failure)

def _execute_with_plan(plan: tuple, instance: object, prefix: str) -> None:
    """
    Execute a pre-resolved plan and raise when any rule fails.

    Parameters
    ----------
    plan : tuple
        Non-empty plan produced by ``_build_plan`` for this instance's type.
    instance : object
        Schema instance to validate.
    prefix : str
        Dot-terminated path prefix for nested field names.

    Raises
    ------
    ValidationException
        Raised with every rule failure found.
    """
    failures: list = []
    _collect_with_plan(plan, instance, prefix, failures)
    if failures:
        raise ValidationException(failures)

def _execute(instance: object, _prefix: str = "") -> None:
    """
    Validate an instance recursively using cached field rules.

    Parameters
    ----------
    instance : object
        Schema instance to validate.
    _prefix : str, default ""
        Dot-separated path prefix used to qualify nested field names.

    Returns
    -------
    None
        Return ``None`` when validation succeeds.

    Raises
    ------
    ValidationException
        Raise when a rule validation fails.
    """
    klass = type(instance)
    plan = _cache_get(klass)
    if plan is None:
        plan = _build_plan(klass)
    if plan:
        _execute_with_plan(plan, instance, _prefix)

class RulesExecutor:

    # Exposed for external inspection; backed by the module-level _PLAN_CACHE.
    _cache = _PLAN_CACHE

    @staticmethod
    def execute(instance: object, *, _prefix: str = "") -> None:
        """
        Validate an instance using its declared metadata rules.

        Parameters
        ----------
        instance : object
            Instance whose fields and rules will be validated.
        _prefix : str
            Internal dot-separated path prefix used when recursing into
            nested schemas (e.g. ``"address"`` so that failures report
            ``"address.code"`` instead of just ``"code"``).
            Callers should not set this parameter directly.

        Returns
        -------
        None
            Return ``None`` when validation succeeds.

        Raises
        ------
        ValidationException
            Raise when one or more validation failures are found.
        """
        _execute(instance, _prefix)
