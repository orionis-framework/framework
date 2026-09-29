from __future__ import annotations
import types
from collections.abc import Mapping
from typing import Annotated, Union, get_args, get_origin
import msgspec
import msgspec.structs
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.exception_parser import ValidationErrorParser
from orionis.schemas.rules_executor import (
    _build_plan as _build_rule_plan,
    _cache_get as _rule_plan_get,
    _collect_with_plan,
)

# Alias msgspec entry points for faster local access on the error path.
_convert = msgspec.convert
_ValidationError = msgspec.ValidationError

# Cache: schema type -> tuple of
# (encode_name, field_type, required, nested, rules).
_FIELD_PLAN_CACHE: dict[type, tuple] = {}

# Alias for faster local access.
_plan_get = _FIELD_PLAN_CACHE.get

def _nested_schema(tp: object) -> type | None:
    """
    Return the Orionis schema wrapped by a field annotation, if any.

    Parameters
    ----------
    tp : object
        Field annotation, possibly wrapped in ``Annotated`` or a union.

    Returns
    -------
    type | None
        Nested schema class, or ``None`` when the field holds no schema.
    """
    origin = get_origin(tp)

    # Annotated only carries metadata, so inspect the wrapped type.
    if origin is Annotated:
        return _nested_schema(get_args(tp)[0])

    # Unions may declare the schema in any member.
    if origin is Union or origin is types.UnionType:
        for arg in get_args(tp):
            found = _nested_schema(arg)
            if found is not None:
                return found
        return None

    if isinstance(tp, type) and "__orionis_meta__" in tp.__dict__:
        return tp
    return None

def _field_plan(schema: type) -> tuple:
    """
    Return a cached per-field plan used to convert a payload field by field.

    Parameters
    ----------
    schema : type
        Schema class whose msgspec fields are inspected.

    Returns
    -------
    tuple
        Entries of ``(encode_name, field_type, required, nested_schema,
        rules)``, where ``rules`` holds the bound custom rule validators
        declared for the field.
    """
    cached = _plan_get(schema)
    if cached is not None:
        return cached

    # Reuse the rule plan already compiled by the executor so custom rules are
    # declared in a single place.
    rule_plan = _rule_plan_get(schema)
    if rule_plan is None:
        rule_plan = _build_rule_plan(schema)
    rules_by_name = {entry[0]: entry[3] for entry in rule_plan}

    plan = tuple(
        (
            f.encode_name,
            f.type,
            f.required,
            _nested_schema(f.type),
            rules_by_name.get(f.name, ()),
        )
        for f in msgspec.structs.fields(schema)
    )
    _FIELD_PLAN_CACHE[schema] = plan
    return plan

class FailureCollector:

    # Prevent per-instance dictionaries; the class is used statically.
    __slots__ = ()

    @classmethod
    def collect(
        cls,
        payload: object,
        schema: type,
        error: msgspec.ValidationError,
    ) -> tuple[ValidationFailure, ...]:
        """
        Collect every conversion and rule failure contained in a payload.

        msgspec stops at the first offending value, so the payload is
        re-converted field by field to report all of them at once. Fields that
        convert cleanly still run their custom rules, so type and rule errors
        are reported together. This runs only after a whole-payload conversion
        has already failed, keeping the successful path at full msgspec speed.

        Parameters
        ----------
        payload : object
            Raw input data that failed conversion.
        schema : type
            Schema class the payload was converted against.
        error : msgspec.ValidationError
            Original error raised by the whole-payload conversion.

        Returns
        -------
        tuple[ValidationFailure, ...]
            Every failure found, including the original parsed error when no
            field could be blamed for it.
        """
        failures: list[ValidationFailure] = []
        blamed = False

        if isinstance(payload, Mapping):
            blamed = cls._collect(payload, schema, schema, "", failures)

        # Keep the original error when no field could be blamed for it
        # (non-mapping payloads, unknown fields, custom struct hooks).
        if not blamed:
            failures.insert(0, ValidationErrorParser.parse(error, schema))

        return tuple(failures)

    @classmethod
    def _collect(
        cls,
        payload: Mapping,
        schema: type,
        root: type,
        base: str,
        failures: list[ValidationFailure],
    ) -> bool:
        """
        Convert each declared field of a mapping and accumulate its failures.

        Parameters
        ----------
        payload : Mapping
            Mapping holding the values for ``schema``.
        schema : type
            Schema class owning the fields being converted.
        root : type
            Root schema class, used to resolve custom messages by path.
        base : str
            Dotted path of ``payload`` relative to the root schema.
        failures : list[ValidationFailure]
            Accumulator receiving every failure found.

        Returns
        -------
        bool
            Return ``True`` when at least one declared field was blamed for a
            conversion error, so the original error needs no separate report.
        """
        # Whether a concrete field explained the original conversion error.
        blamed = False

        # Values that converted cleanly, reused to run custom rules afterwards.
        converted_values: dict[str, object] = {}

        # Fields carrying custom rules or a nested schema, deferred until every
        # value is known so rules can inspect their sibling fields.
        pending: list[tuple[str, object, tuple, type | None]] = []

        for name, field_type, required, nested, rules in _field_plan(schema):

            # Report absent values instead of letting the conversion fail.
            if name not in payload:
                if required:
                    blamed = True
                    failures.append(
                        ValidationFailure(
                            field=base + name,
                            rule="missing",
                            message=f"Object missing required field `{name}`",
                        ),
                    )
                continue

            value = payload[name]
            try:
                converted = _convert(value, type=field_type)
            except _ValidationError as exc:
                blamed = True
                failures.extend(
                    cls._blame(exc, value, nested, root, base + name),
                )
                continue

            converted_values[name] = converted
            if rules or nested is not None:
                pending.append((base + name, converted, rules, nested))

        if pending:
            cls._enforce(pending, converted_values, failures)

        return blamed

    @classmethod
    def _enforce(
        cls,
        pending: list[tuple[str, object, tuple, type | None]],
        converted_values: dict[str, object],
        failures: list[ValidationFailure],
    ) -> None:
        """
        Run custom rules over the field values that converted successfully.

        Type errors abort the whole-payload conversion, so no schema instance
        exists on this path. Rules receive a namespace holding only the fields
        that converted cleanly, which keeps cross-field rules usable while
        still reporting type and rule failures together.

        Parameters
        ----------
        pending : list[tuple[str, object, tuple, type | None]]
            Entries of ``(path, value, rules, nested_schema)`` to check.
        converted_values : dict[str, object]
            Successfully converted values, keyed by encoded field name.
        failures : list[ValidationFailure]
            Accumulator receiving every failure found.

        Returns
        -------
        None
            Return ``None`` after running every pending rule.
        """
        instance = types.SimpleNamespace(**converted_values)

        for path, value, rules, nested in pending:

            # Nested schemas converted fine, so their own rules run as usual.
            if nested is not None and value is not None:
                child_plan = _rule_plan_get(type(value))
                if child_plan is None:
                    child_plan = _build_rule_plan(type(value))
                if child_plan:
                    _collect_with_plan(child_plan, value, path + ".", failures)

            for validate in rules:
                failure = validate(path, value, instance)
                if failure is not None:
                    failures.append(failure)

    @classmethod
    def _blame(
        cls,
        error: msgspec.ValidationError,
        value: object,
        nested: type | None,
        root: type,
        path: str,
    ) -> list[ValidationFailure]:
        """
        Describe every failure behind a single rejected field value.

        Parameters
        ----------
        error : msgspec.ValidationError
            Error raised while converting the field value.
        value : object
            Rejected field value.
        nested : type | None
            Schema declared by the field, when it holds a nested schema.
        root : type
            Root schema class, used to resolve custom messages by path.
        path : str
            Dotted path of the field relative to the root schema.

        Returns
        -------
        list[ValidationFailure]
            Failures of the nested schema, or a single parsed failure.
        """
        # Recurse so nested schemas also report all their failures.
        if nested is not None and isinstance(value, Mapping):
            nested_failures: list[ValidationFailure] = []
            cls._collect(value, nested, root, path + ".", nested_failures)
            if nested_failures:
                return nested_failures

        return [ValidationErrorParser.parseAt(error, root, path)]
