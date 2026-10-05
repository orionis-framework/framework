from __future__ import annotations
import types
from collections.abc import Mapping
from typing import Annotated, Union, get_args, get_origin
import msgspec
import msgspec.structs
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.exception_parser import ValidationErrorParser
from orionis.schemas.rules_executor import (
    _async_validators,
    _build_plan as _build_rule_plan,
    _cache_get as _rule_plan_get,
    _collect_async_nested,
    _collect_async_rules,
    _collect_nested,
)

# Bind the msgspec conversion entry point.
_convert = msgspec.convert
_ValidationError = msgspec.ValidationError

# Cache: schema type -> tuple of
# (encode_name, field_type, required, nested, rules).
_FIELD_PLAN_CACHE: dict[type, tuple] = {}
_ASYNC_FIELD_PLAN_CACHE: dict[type, tuple] = {}

# Bind the field plan lookup.
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

def _async_field_plan(schema: type) -> tuple:
    """
    Reuse conversion metadata with preclassified asynchronous validators.

    Parameters
    ----------
    schema : type
        Schema whose payload failed whole-object conversion.

    Returns
    -------
    tuple
        Cached field conversion plans with await flags for their rule callables.
    """
    plan = _ASYNC_FIELD_PLAN_CACHE.get(schema)
    if plan is None:
        plan = tuple(
            (name, field_type, required, nested, _async_validators(rules))
            for name, field_type, required, nested, rules in _field_plan(schema)
        )
        _ASYNC_FIELD_PLAN_CACHE[schema] = plan
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
                _collect_nested(value, path + ".", failures)

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

    @classmethod
    async def collectAsync(
        cls,
        payload: object,
        schema: type,
        error: msgspec.ValidationError,
    ) -> tuple[ValidationFailure, ...]:
        """
        Collect conversion failures together with asynchronous rule failures.

        Parameters
        ----------
        payload : object
            Raw input rejected by whole-object conversion.
        schema : type
            Target schema class.
        error : msgspec.ValidationError
            Original conversion failure.

        Returns
        -------
        tuple[ValidationFailure, ...]
            Conversion and rule failures in the same order as synchronous checks.
        """
        failures: list[ValidationFailure] = []
        blamed = False
        if isinstance(payload, Mapping):
            blamed = await cls._collectAsync(payload, schema, schema, "", failures)
        if not blamed:
            failures.insert(0, ValidationErrorParser.parse(error, schema))
        return tuple(failures)

    @classmethod
    async def _collectAsync(
        cls,
        payload: Mapping,
        schema: type,
        root: type,
        base: str,
        failures: list[ValidationFailure],
    ) -> bool:
        """
        Convert fields before awaiting rules that inspect their valid siblings.

        Parameters
        ----------
        payload : Mapping
            Values supplied for the current schema.
        schema : type
            Schema whose fields are being converted.
        root : type
            Root schema used to resolve custom error messages.
        base : str
            Dot-terminated path prefix.
        failures : list[ValidationFailure]
            Accumulator for conversion and rule failures.

        Returns
        -------
        bool
            Whether a declared field explains the original conversion failure.
        """
        blamed = False
        converted_values: dict[str, object] = {}
        pending: list[tuple[str, object, tuple, type | None]] = []
        for name, field_type, required, nested, rules in _async_field_plan(schema):
            if name not in payload:
                if required:
                    blamed = True
                    failures.append(ValidationFailure(
                        field=base + name, rule="missing",
                        message=f"Object missing required field `{name}`",
                    ))
                continue
            value = payload[name]
            try:
                converted = _convert(value, type=field_type)
            except _ValidationError as exc:
                blamed = True
                failures.extend(await cls._blameAsync(
                    exc, value, nested, root, base + name,
                ))
                continue
            converted_values[name] = converted
            if rules or nested is not None:
                pending.append((base + name, converted, rules, nested))
        if pending:
            await cls._enforceAsync(pending, converted_values, failures)
        return blamed

    @staticmethod
    async def _enforceAsync(
        pending: list[tuple[str, object, tuple, type | None]],
        converted_values: dict[str, object],
        failures: list[ValidationFailure],
    ) -> None:
        """
        Await custom rules only for fields that converted successfully.

        Parameters
        ----------
        pending : list[tuple[str, object, tuple, type | None]]
            Qualified paths, values, rules and nested schema declarations.
        converted_values : dict[str, object]
            Valid field values available to cross-field rules.
        failures : list[ValidationFailure]
            Accumulator for rule failures.

        Returns
        -------
        None
            Every applicable rule has completed in declaration order.
        """
        instance = types.SimpleNamespace(**converted_values)
        for path, value, rules, nested in pending:
            if nested is not None and value is not None:
                await _collect_async_nested(value, path + ".", failures)
            if rules:
                await _collect_async_rules(rules, path, value, instance, failures)

    @classmethod
    async def _blameAsync(
        cls,
        error: msgspec.ValidationError,
        value: object,
        nested: type | None,
        root: type,
        path: str,
    ) -> list[ValidationFailure]:
        """
        Describe a rejected value, awaiting valid fields of nested schemas.

        Parameters
        ----------
        error : msgspec.ValidationError
            Error raised by the field conversion.
        value : object
            Rejected input value.
        nested : type | None
            Nested schema declared for the field.
        root : type
            Root schema used to resolve error messages.
        path : str
            Fully qualified field path.

        Returns
        -------
        list[ValidationFailure]
            Nested failures or the parsed field conversion error.
        """
        if nested is not None and isinstance(value, Mapping):
            nested_failures: list[ValidationFailure] = []
            await cls._collectAsync(value, nested, root, path + ".", nested_failures)
            if nested_failures:
                return nested_failures
        return [ValidationErrorParser.parseAt(error, root, path)]
