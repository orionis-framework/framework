from __future__ import annotations
import types
from collections.abc import Collection, Mapping
from typing import TYPE_CHECKING, Annotated, Union, get_args, get_origin
import msgspec
import msgspec.structs
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.constraint_plan import annotation_messages, constraint_plan
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
_INVALID = object()

# Cache: schema type -> tuple of
# (encode_name, field_type, required, nested, rules, attribute, default, factory).
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
    Return a cached plan for collecting field validation failures.

    Parameters
    ----------
    schema : type
        Schema class whose msgspec fields are inspected.

    Returns
    -------
    tuple
        Entries of ``(encode_name, field_type, required, nested_annotation,
        rules, attribute, default, factory)``, where ``rules`` holds the bound
        custom validators and ``attribute`` is the Python field name.
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
            rules_by_name.get(f.encode_name, ()),
            f.name,
            f.default,
            f.default_factory,
        )
        for f in msgspec.structs.fields(schema)
    )
    _FIELD_PLAN_CACHE[schema] = plan
    return plan

def _payload_fields(payload: Mapping | list | tuple, schema: type) -> Mapping:
    """
    Map array-like schema positions to encoded field names.

    Parameters
    ----------
    payload : Mapping | list | tuple
        Field mapping or positional schema data, including any tag.
    schema : type
        Schema defining field order, encoded names and tag configuration.

    Returns
    -------
    Mapping
        Original mapping or positional values keyed by encoded field name.
    """
    if isinstance(payload, Mapping):
        return payload
    offset = int(schema.__struct_config__.tag is not None)
    return {
        entry[0]: value
        for entry, value in zip(_field_plan(schema), payload[offset:], strict=False)
    }

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
        Collect conversion, constraint and rule failures from a rejected payload.

        Inspect fields only after whole-payload conversion fails. Run custom
        rules on type-compatible values, even when their constraints fail.

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

        if isinstance(payload, Mapping) or (
            schema.__struct_config__.array_like
            and isinstance(payload, list | tuple)
        ):
            blamed = await cls._collect(payload, schema, schema, "", failures)

        # Keep the original error when no field could be blamed for it
        # (non-mapping payloads, unknown fields, custom struct hooks).
        if not blamed:
            failures.insert(0, ValidationErrorParser.parse(error, schema))

        return tuple(failures)

    @classmethod
    async def _collect(
        cls,
        payload: Mapping | list | tuple,
        schema: type,
        root: type,
        base: str,
        failures: list[ValidationFailure],
    ) -> bool:
        """
        Convert declared fields and accumulate their validation failures.

        Parameters
        ----------
        payload : Mapping | list | tuple
            Field mapping or positional data for an array-like schema.
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
            Whether a declared field explains the original conversion error.
        """
        # Whether a concrete field explained the original conversion error.
        blamed = False

        payload = _payload_fields(payload, schema)

        # Values that converted cleanly, reused to run custom rules afterwards.
        converted_values: dict[str, object] = {}

        # Fields carrying custom rules or a nested schema, deferred until every
        # value is known so rules can inspect their sibling fields.
        pending: list[tuple[str, object, tuple, object | None]] = []

        for (
            name, field_type, required, nested, rules, attribute, default, factory,
        ) in _field_plan(schema):

            if name in payload:
                value = payload[name]
            elif required:
                blamed = True
                failures.append(
                    ValidationFailure(
                        field=base + name,
                        rule="missing",
                        message=f"Object missing required field `{name}`",
                    ),
                )
                continue
            elif default is not msgspec.NODEFAULT:
                value = default
            elif factory is not msgspec.NODEFAULT:
                value = factory()
            else:
                continue
            try:
                converted = _convert(value, type=field_type)
            except _ValidationError as exc:
                blamed = True
                converted, field_failures = await cls._recover(
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
                if converted is _INVALID:
                    continue

            converted_values[attribute] = converted
            if rules or nested is not None:
                pending.append((base + name, converted, rules, nested))

        await cls._enforce(pending, converted_values, failures)

        return blamed

    @classmethod
    async def _recover(
        cls, error: msgspec.ValidationError, value: object,
        annotation: object, root: type, path: str,
    ) -> tuple[object, list[ValidationFailure]]:
        """
        Recover a type-compatible value and collect its validation failures.

        Parameters
        ----------
        error : msgspec.ValidationError
            Error raised by the original field conversion.
        value : object
            Rejected field value.
        annotation : object
            Declared field type and metadata.
        root : type
            Schema used to resolve custom messages.
        path : str
            Field path relative to ``root``.

        Returns
        -------
        tuple[object, list[ValidationFailure]]
            Converted value and failures, or ``_INVALID`` and failures when
            the value remains structurally incompatible.
        """
        base_type, probes = constraint_plan(annotation)
        if probes:
            try:
                converted = _convert(value, type=base_type)
            except _ValidationError:
                pass
            else:
                # Failed constraints do not make a correctly typed value
                # unsafe for rules, including checks against sibling values.
                return converted, cls._constraints(value, probes, root, path)
        return _INVALID, await cls._blame(error, value, annotation, root, path)

    @staticmethod
    def _constraints(
        value: object, probes: tuple, root: type, path: str,
    ) -> list[ValidationFailure]:
        """
        Collect independent constraint failures with their declared codes.

        Parameters
        ----------
        value : object
            Field value checked by each constraint probe.
        probes : tuple
            Entries of ``(rule_code, annotation, custom_message)``.
        root : type
            Schema supplying fallback field messages.
        path : str
            Field path used to locate messages and report failures.

        Returns
        -------
        list[ValidationFailure]
            Local constraint failures, excluding type and child errors.
        """
        failures = []
        for code, annotation, local_message in probes:
            try:
                _convert(value, type=annotation)
            except _ValidationError as exc:
                failure = ValidationErrorParser.parseAt(exc, root, path)
                # Ignore incompatible types and failures belonging to children;
                # those are reported by the structural traversal instead.
                if failure.field == path and failure.rule != "type":
                    messages = getattr(root, "__orionis_constraints__", {})
                    custom = (
                        local_message if local_message is not None
                        else messages.get(path, {}).get(code)
                    )
                    failures.append(ValidationFailure(
                        field=path, rule=code,
                        message=custom if custom is not None else failure.message,
                    ))
        return failures

    @classmethod
    async def _enforce(
        cls,
        pending: list[tuple[str, object, tuple, object | None]],
        converted_values: dict[str, object],
        failures: list[ValidationFailure],
    ) -> None:
        """
        Run nested and field rules over type-compatible values.

        Supply converted sibling values through a namespace because the
        failed whole-payload conversion produced no schema instance.

        Parameters
        ----------
        pending : list[tuple[str, object, tuple, object | None]]
            Entries of ``(path, value, rules, nested_annotation)`` to check.
        converted_values : dict[str, object]
            Type-compatible values, including defaults, keyed by attribute name.
        failures : list[ValidationFailure]
            Accumulator receiving every failure found.

        Returns
        -------
        None
            Append rule failures to ``failures``.
        """
        if not pending:
            return
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
        Collect local and nested failures for a rejected field value.

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
            Constraint and child failures, or the parsed original error.
        """
        base_type, probes = constraint_plan(nested)
        failures = cls._constraints(value, probes, root, path)
        annotation = cls._matchingType(base_type, value)
        schema = _nested_schema(annotation)
        if schema is not None:
            nested_failures: list[ValidationFailure] = []
            await cls._collect(value, schema, schema, path + ".", nested_failures)
            if nested_failures:
                return failures + nested_failures

        if annotation is not None and get_origin(annotation) is not None:
            children = await cls._blameCollection(error, value, annotation, root, path)
            known = {(failure.field, failure.rule) for failure in failures}
            failures.extend(
                failure for failure in children
                if (failure.field, failure.rule) not in known
            )
            return failures

        if failures:
            return failures
        original = ValidationErrorParser.parseAt(error, root, path)
        custom = annotation_messages(nested).get(original.rule)
        if custom is not None:
            original = ValidationFailure(
                field=original.field, rule=original.rule, message=custom,
            )
        return [original]

    @classmethod
    def _matchingType(cls, annotation: object, value: object) -> object | None:
        """
        Select a nested annotation matching the value's shape and schema tag.

        Parameters
        ----------
        annotation : object
            Field or element annotation, possibly annotated or a union.
        value : object
            Rejected input used to match object or array-like representations.

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
            return cls._matchingSchema(schema, value)
        if not isinstance(origin, type):
            return None
        expected = (
            Mapping if issubclass(origin, Mapping) else (list, tuple, set, frozenset)
        )
        return annotation if (
            issubclass(origin, Collection) and isinstance(value, expected)
        ) else None

    @staticmethod
    def _matchingSchema(
        schema: type[msgspec.Struct], value: object,
    ) -> type[msgspec.Struct] | None:
        """
        Match a schema's object or array representation and optional tag.

        Parameters
        ----------
        schema : type[msgspec.Struct]
            Schema class whose representation is checked.
        value : object
            Rejected input to compare with the schema configuration.

        Returns
        -------
        type[msgspec.Struct] | None
            Schema when its shape and tag match, otherwise ``None``.
        """
        config = schema.__struct_config__
        if config.array_like:
            return schema if (
                isinstance(value, list | tuple)
                and (config.tag is None or (value and value[0] == config.tag))
            ) else None
        return schema if (
            isinstance(value, Mapping)
            and (config.tag is None or value.get(config.tag_field) == config.tag)
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
