from __future__ import annotations
import types
from collections.abc import Collection, Mapping
from typing import TYPE_CHECKING, Annotated, Union, get_args, get_origin
import msgspec
import msgspec.structs
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.exception_parser import ValidationErrorParser
from orionis.schemas.rules_executor import (
    _build_plan as _build_rule_plan,
    _cache_get as _rule_plan_get,
    _collect_nested,
    _collection_item_type,
    _type_contains_nested,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

# Bind the msgspec conversion entry point.
_convert = msgspec.convert
_ValidationError = msgspec.ValidationError

# Cache: schema type -> tuple of
# (encode_name, field_type, required, nested, rules).
_FIELD_PLAN_CACHE: dict[type, tuple] = {}

# Bind the field plan lookup.
_plan_get = _FIELD_PLAN_CACHE.get

def _nested_schema(tp: object) -> type[msgspec.Struct] | None:
    """
    Return the Orionis schema wrapped by a field annotation, if any.

    Parameters
    ----------
    tp : object
        Field annotation, possibly wrapped in ``Annotated`` or a union.

    Returns
    -------
    type[msgspec.Struct] | None
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

    if (
        isinstance(tp, type)
        and issubclass(tp, msgspec.Struct)
        and "__orionis_meta__" in tp.__dict__
    ):
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
        Entries of ``(encode_name, field_type, required, nested_annotation,
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
            _nested_schema(f.type) or (
                f.type if _type_contains_nested(f.type) else None
            ),
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
    async def collect(
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
            blamed = await cls._collect(payload, schema, schema, "", failures)

        # Keep the original error when no field could be blamed for it
        # (non-mapping payloads, unknown fields, custom struct hooks).
        if not blamed:
            failures.insert(0, ValidationErrorParser.parse(error, schema))

        return tuple(failures)

    @classmethod
    async def _collect(
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
        pending: list[tuple[str, object, tuple, object | None]] = []

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
                field_failures = await cls._blame(
                    exc, value, field_type, root, name,
                )
                failures.extend(
                    ValidationFailure(
                        field=base + failure.field,
                        rule=failure.rule,
                        message=failure.message,
                    )
                    for failure in field_failures
                )
                continue

            converted_values[name] = converted
            if rules or nested is not None:
                pending.append((base + name, converted, rules, nested))

        if pending:
            await cls._enforce(pending, converted_values, failures)

        return blamed

    @classmethod
    async def _enforce(
        cls,
        pending: list[tuple[str, object, tuple, object | None]],
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
        pending : list[tuple[str, object, tuple, object | None]]
            Entries of ``(path, value, rules, nested_annotation)`` to check.
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
                await _collect_nested(value, path + ".", failures)

            for validate in rules:
                failure = await validate(path, value, instance)
                if failure is not None:
                    failures.append(failure)

    @classmethod
    async def _blame(
        cls,
        error: msgspec.ValidationError,
        value: object,
        nested: object | None,
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
        nested : object | None
            Annotation declared by the field being converted.
        root : type
            Root schema class, used to resolve custom messages by path.
        path : str
            Dotted path of the field relative to the root schema.

        Returns
        -------
        list[ValidationFailure]
            Failures of the nested schema, or a single parsed failure.
        """
        annotation = (
            cls._matchingType(nested, value)
            if _type_contains_nested(nested) else None
        )
        schema = _nested_schema(annotation)
        if schema is not None and isinstance(value, Mapping):
            nested_failures: list[ValidationFailure] = []
            await cls._collect(value, schema, schema, path + ".", nested_failures)
            if nested_failures:
                return nested_failures

        if annotation is not None and get_origin(annotation) is not None:
            return await cls._blameCollection(error, value, annotation, root, path)

        return [ValidationErrorParser.parseAt(error, root, path)]

    @classmethod
    def _matchingType(cls, annotation: object, value: object) -> object | None:
        """
        Select the nested annotation matching a rejected value's shape.

        Parameters
        ----------
        annotation : object
            Field or element annotation, possibly annotated or a union.
        value : object
            Rejected input used to distinguish maps from sequences.

        Returns
        -------
        object | None
            Matching schema or collection annotation, if one applies.
        """
        origin = get_origin(annotation)
        if origin is Annotated:
            return cls._matchingType(get_args(annotation)[0], value)
        if origin is Union or origin is types.UnionType:
            return next((
                match for arg in get_args(annotation)
                if (match := cls._matchingType(arg, value)) is not None
            ), None)
        schema = _nested_schema(annotation)
        if schema is not None:
            config = schema.__struct_config__
            return schema if (
                isinstance(value, Mapping)
                and (config.tag is None or value.get(config.tag_field) == config.tag)
            ) else None
        if not isinstance(origin, type):
            return None
        expected = (
            Mapping if issubclass(origin, Mapping) else (list, tuple, set, frozenset)
        )
        return annotation if (
            issubclass(origin, Collection) and isinstance(value, expected)
        ) else None

    @classmethod
    async def _blameCollection(
        cls,
        error: msgspec.ValidationError,
        value: object,
        annotation: object,
        root: type,
        path: str,
    ) -> list[ValidationFailure]:
        """
        Collect conversion and rule failures independently for each child.

        Parameters
        ----------
        error : msgspec.ValidationError
            Error raised by converting the entire collection.
        value : object
            Collection selected by ``_matchingType``.
        annotation : object
            Concrete collection annotation.
        root : type
            Root schema used to resolve custom messages.
        path : str
            Fully qualified collection path.

        Returns
        -------
        list[ValidationFailure]
            Collection-level failures and failures from every child.
        """
        args = get_args(annotation)
        items: Iterable[tuple[str, object, object]]
        if isinstance(value, Mapping):
            items = (
                (f"{path}[{key!r}]", item, args[1])
                for key, item in value.items()
            )
        elif isinstance(value, list | tuple | set | frozenset):
            items = (
                (f"{path}[{index}]", item, item_type)
                for index, item in enumerate(value)
                if (
                    item_type := _collection_item_type(annotation, str(index))
                ) is not None
            )
        else:
            return [ValidationErrorParser.parseAt(error, root, path)]

        failures: list[ValidationFailure] = []
        blamed = False
        for item_path, item, item_type in items:
            try:
                converted = _convert(item, type=item_type)
            except _ValidationError as exc:
                blamed = True
                failures.extend(await cls._blame(
                    exc, item, item_type, root, item_path,
                ))
            else:
                await _collect_nested(converted, item_path + ".", failures)

        original = ValidationErrorParser.parseAt(error, root, path)
        if not blamed or original.field == path:
            failures.insert(0, original)
        return failures
