from __future__ import annotations
import re
import types
import msgspec
import msgspec.structs
from typing import Annotated, Union, get_args, get_origin
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.rules_executor import _collection_item_type

# Regular expressions for parsing msgspec error messages.
MISSING_FIELD_RE = re.compile(r"missing required field `(?P<field>[^`]+)`")

# Keep quoted dictionary keys intact even when they contain dots or brackets.
_PATH_PART_RE = re.compile(
    r"""(?:^|\.)(?P<field>[^.\[\]]+)|"""
    r"""\[(?P<key>'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*"|[^\]'"]*)\]""",
)

# Suffix msgspec appends to report the location of the offending value.
_PATH_MARKER = " - at `$"
_PATH_MARKER_LEN = len(_PATH_MARKER)

# Ordered patterns for identifying constraint types from msgspec error messages.
_CONSTRAINT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("of length >=", "min_length"),
    ("of length <=", "max_length"),
    ("matching regex", "pattern"),
    ("multiple of", "multiple_of"),
    ("no timezone", "tz_naive"),
    ("timezone", "tz_aware"),
    (" >= ", "ge"),
    (" <= ", "le"),
    (" > ", "gt"),
    (" < ", "lt"),
    ("Expected", "type"),
)

# Sentinel for distinguishing "not in cache" from "cached result is None".
_MISSING: object = object()

# Cache: schema_type → {field_name: field_type} built from msgspec.structs.fields().
# Avoids repeated C-level calls to fields() on the error path.
_STRUCT_FIELDS_MAP: dict[type, dict[str, object]] = {}

# Cache: (schema_type, field_name) → nested schema type or None.
_NESTED_TYPE_CACHE: dict[tuple[type, str], type | None] = {}

def _get_fields_map(schema: type) -> dict[str, object]:
    """
    Return a cached field-to-type mapping for a schema.

    Parameters
    ----------
    schema : type
        Msgspec struct class whose fields should be inspected.

    Returns
    -------
    dict[str, object]
        Mapping of field names to their declared types.
    """
    cached = _STRUCT_FIELDS_MAP.get(schema)
    if cached is not None:
        return cached
    m = {f.name: f.type for f in msgspec.structs.fields(schema)}
    _STRUCT_FIELDS_MAP[schema] = m
    return m

class ValidationErrorParser:

    # Prevent per-instance dictionaries; the class is used statically.
    __slots__ = ()

    @classmethod
    def parse(
        cls,
        error: msgspec.ValidationError,
        schema: type | None = None,
    ) -> ValidationFailure:
        """
        Parse a msgspec validation error into framework failures.

        Parameters
        ----------
        error : msgspec.ValidationError
            Provide the original validation exception.
        schema : type | None
            Optional schema class used to look up custom constraint messages.

        Returns
        -------
        ValidationFailure
            Return a single validation failure describing the parsed error.
        """
        return cls.parseAt(error, schema, "")

    @classmethod
    def parseAt(
        cls,
        error: msgspec.ValidationError,
        schema: type | None,
        base: str,
    ) -> ValidationFailure:
        """
        Parse a msgspec validation error raised while converting a sub-value.

        Parameters
        ----------
        error : msgspec.ValidationError
            Provide the original validation exception.
        schema : type | None
            Root schema class used to look up custom constraint messages.
        base : str
            Dotted path of the value being converted, relative to the root
            schema (``""`` when the error comes from the root payload).

        Returns
        -------
        ValidationFailure
            Return a single validation failure with a fully-qualified field.
        """
        text = str(error)

        # Separate the validation message from its field path.
        marker = text.rfind(_PATH_MARKER)
        if (
            marker > 0
            and text.endswith("`")
            and "`" not in (path := text[marker + _PATH_MARKER_LEN : -1])
        ):
            raw_message = text[:marker]
            field = cls._joinPath(base, path.lstrip("."))
        else:
            missing = MISSING_FIELD_RE.search(text)

            # Missing fields carry their own name instead of a path suffix.
            if missing is not None:
                return ValidationFailure(
                    field=cls._joinPath(base, missing.group("field")),
                    rule="missing",
                    message=text,
                )

            # Errors on the converted value itself report no path at all.
            raw_message = text
            field = base

        constraint_key = cls._matchConstraintKey(raw_message)
        rule = constraint_key if constraint_key is not None else "type"

        # Replace the default msgspec message with the custom one when available.
        message = raw_message
        if schema is not None and field:
            custom = cls._customMessage(schema, field, raw_message)
            if custom is not None:
                message = custom

        return ValidationFailure(
            field=field,
            rule=rule,
            message=message,
        )

    @staticmethod
    def _joinPath(base: str, relative: str) -> str:
        """
        Concatenate a base field path with a relative msgspec path.

        Parameters
        ----------
        base : str
            Dotted path of the value being converted.
        relative : str
            Path reported by msgspec, relative to that value.

        Returns
        -------
        str
            Fully-qualified dotted field path.
        """
        if not base:
            return relative
        if not relative:
            return base

        # Sequence indices are appended without a separating dot.
        if relative[0] == "[":
            return base + relative
        return base + "." + relative

    @classmethod
    def _customMessage(
        cls,
        schema: type,
        field_path: str,
        raw_msg: str,
    ) -> str | None:
        """
        Return a custom error message for a failed constraint, if one is set.

        Parameters
        ----------
        schema : type
            Root schema class.
        field_path : str
            Dot-separated field path (e.g. ``"address.code"`` or ``"name"``)
            as produced by parsing the msgspec error.
        raw_msg : str
            The raw constraint error message emitted by msgspec.

        Returns
        -------
        str | None
            The custom message, or ``None`` when none is configured.
        """
        leaf_schema, leaf_field = cls._resolveSchema(schema, field_path)
        constraints: dict[str, dict[str, str]] = getattr(
            leaf_schema, "__orionis_constraints__", {},
        )
        field_constraints = constraints.get(leaf_field)
        if not field_constraints:
            return None
        constraint_key = cls._matchConstraintKey(raw_msg)
        if constraint_key is None:
            return None
        return field_constraints.get(constraint_key)

    @staticmethod
    def _resolveSchema(schema: type, field_path: str) -> tuple[type, str]:
        """
        Traverse the schema hierarchy and return ``(leaf_schema, leaf_field)``.

        For a path like ``"address.zip_code"`` starting from ``UserSchema``
        this returns ``(AddressSchema, "zip_code")``.

        Parameters
        ----------
        schema : type
            Root schema class to start traversal from.
        field_path : str
            Dot-separated field path.

        Returns
        -------
        tuple[type, str]
            ``(leaf_schema_class, leaf_field_name)`` pair.
        """
        # Handle field names without nested segments.
        if "." not in field_path:
            return schema, field_path

        parts: list[str] = []
        for match in _PATH_PART_RE.finditer(field_path):
            if match.group("field") is not None:
                parts.append(match.group("field"))
            elif parts:
                parts[-1] += match.group(0)
        current: type = schema

        for part in parts[:-1]:
            resolved = ValidationErrorParser._resolveNestedType(current, part)
            if resolved is None:
                return schema, field_path
            current = resolved

        return current, parts[-1]

    @staticmethod
    def _resolveNestedType(schema: type, field_name: str) -> type | None:
        """
        Return the nested schema type for ``field_name`` within ``schema``.

        Parameters
        ----------
        schema : type
            Parent schema class to inspect.
        field_name : str
            Name of the field whose nested schema type is needed.

        Returns
        -------
        type | None
            The nested schema class, or ``None`` when not found.
        """
        # Do not retain request-owned dictionary keys in the type cache.
        indexed = "[" in field_name
        key = (schema, field_name)
        if not indexed:
            cached = _NESTED_TYPE_CACHE.get(key, _MISSING)
            if cached is not _MISSING:
                return cached

        # Get the declared type of the field from the schema's fields map.
        field_type = _get_fields_map(schema).get(field_name.partition("[")[0])
        selectors = tuple(
            match.group("key") for match in _PATH_PART_RE.finditer(field_name)
            if match.group("key") is not None
        )
        result = ValidationErrorParser._nestedType(field_type, selectors)

        # Cache the result (including None)
        # to avoid redundant lookups on the error path.
        if not indexed:
            _NESTED_TYPE_CACHE[key] = result
        return result

    @staticmethod
    def _nestedType(tp: object, selectors: tuple[str, ...]) -> type | None:
        """
        Follow collection selectors to the schema owning a nested field.

        Parameters
        ----------
        tp : object
            Annotation of the parent field.
        selectors : tuple[str, ...]
            Sequence indices or dictionary keys preceding the nested field.

        Returns
        -------
        type | None
            Schema selected by the annotation and collection path.
        """
        origin = get_origin(tp)
        args = get_args(tp)
        if origin is Annotated:
            return ValidationErrorParser._nestedType(args[0], selectors)
        if origin is Union or origin is types.UnionType:
            for arg in args:
                result = ValidationErrorParser._nestedType(arg, selectors)
                if result is not None:
                    return result
            return None
        if selectors:
            item_type = _collection_item_type(tp, selectors[0])
            return ValidationErrorParser._nestedType(item_type, selectors[1:])
        return (
            tp if isinstance(tp, type) and hasattr(tp, "__orionis_constraints__")
            else None
        )

    @staticmethod
    def _matchConstraintKey(message: str) -> str | None:
        """
        Identify the constraint type from a raw msgspec error message.

        Parameters
        ----------
        message : str
            Raw msgspec constraint violation message (without the path suffix).

        Returns
        -------
        str | None
            The constraint key (e.g. ``"min_length"``, ``"gt"``), or
            ``None`` when no known pattern matches.
        """
        # Scan the ordered patterns and stop at the first phrase present in the
        # message; the ordering encodes the precedence between constraints.
        for substring, key in _CONSTRAINT_PATTERNS:
            if substring in message:
                return key

        # No known pattern matched: return None to indicate a generic "type" error.
        return None
