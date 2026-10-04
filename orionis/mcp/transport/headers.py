"""Compile mirrored tool parameters and validate HTTP metadata against the body."""

from __future__ import annotations

import base64
import binascii
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, DecimalException
from typing import TYPE_CHECKING, Literal, cast

import msgspec

from orionis.mcp.exceptions import McpInvalidParams, McpProtocolException
from orionis.mcp.protocol.constants import PROTOCOL_VERSION

if TYPE_CHECKING:
    from orionis.http.payload.estructures.headers import Headers
    from orionis.mcp.protocol.requests import JsonRpcRequest, RequestParams

type HeaderKind = Literal["string", "integer", "boolean"]

_TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+\Z")
_PLAIN = re.compile(r"(?:[\x21-\x7e](?:[\x09\x20-\x7e]*[\x21-\x7e])?)?\Z")
_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
_SAFE_INTEGER = 9007199254740991
_ANNOTATION = "x-mcp-header"
_PREFIX = "=?base64?"
_SUFFIX = "?="
_NAMED_METHODS = frozenset({"tools/call", "resources/read", "prompts/get"})


@dataclass(frozen=True, slots=True)
class HeaderBinding:
    """One statically reachable argument mirrored into a lowercase HTTP header."""

    path: tuple[str, ...]
    name: str
    kind: HeaderKind


def _contains_annotation(value: object) -> bool:
    """Locate annotations even inside unsupported schema constructs."""
    if isinstance(value, Mapping):
        return _ANNOTATION in value or any(
            _contains_annotation(child) for child in value.values()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_annotation(child) for child in value)
    return False


def _binding(schema: Mapping[str, object], path: tuple[str, ...]) -> HeaderBinding:
    """Validate the name and primitive type at one reachable property."""
    name = schema[_ANNOTATION]
    kind = schema.get("type")
    if not isinstance(name, str) or _TOKEN.fullmatch(name) is None:
        message = "x-mcp-header must contain a nonempty HTTP field-name token"
        raise ValueError(message)
    if kind not in ("string", "integer", "boolean"):
        message = "x-mcp-header requires a string, integer, or boolean property"
        raise ValueError(message)
    return HeaderBinding(path, "mcp-param-" + name.lower(), cast("HeaderKind", kind))


def _walk_schema(
    schema: Mapping[str, object],
    path: tuple[str, ...],
    bindings: list[HeaderBinding],
) -> None:
    """Visit properties chains and reject annotations hidden elsewhere."""
    for key, value in schema.items():
        if key == _ANNOTATION:
            if path:
                bindings.append(_binding(schema, path))
                continue
            message = "x-mcp-header is only valid on statically reachable properties"
            raise ValueError(message)
        if key == "properties" and isinstance(value, Mapping):
            for name, child in value.items():
                if isinstance(name, str) and isinstance(child, Mapping):
                    _walk_schema(child, (*path, name), bindings)
        elif _contains_annotation(value):
            message = "x-mcp-header cannot occur outside a properties chain"
            raise ValueError(message)


def compile_header_bindings(
    input_schema: Mapping[str, object],
) -> tuple[HeaderBinding, ...]:
    """Validate tool schema annotations once and freeze extraction paths."""
    bindings: list[HeaderBinding] = []
    _walk_schema(input_schema, (), bindings)
    names = {binding.name for binding in bindings}
    if len(names) != len(bindings):
        message = "x-mcp-header names must be case-insensitively unique"
        raise ValueError(message)
    return tuple(bindings)


def _mismatch(name: str) -> McpProtocolException:
    """Report the failing header without reflecting untrusted field values."""
    return McpProtocolException(-32020, f"Header mismatch: {name}", status=400)


def _decode_value(value: str, name: str, *, encoded: bool) -> str:
    """Validate ASCII transport syntax and decode the exact Base64 sentinel."""
    if _PLAIN.fullmatch(value) is None:
        raise _mismatch(name)
    if encoded and value.startswith(_PREFIX) and value.endswith(_SUFFIX):
        try:
            return base64.b64decode(
                value[len(_PREFIX) : -len(_SUFFIX)],
                validate=True,
            ).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise _mismatch(name) from exc
    return value


def _single_header(headers: Headers, name: str, *, encoded: bool = False) -> str:
    """Require one field occurrence, including case-insensitive duplicates."""
    if headers.count(name) != 1:
        raise _mismatch(name)
    value = headers.get(name)
    if value is None:
        raise _mismatch(name)
    return _decode_value(value, name, encoded=encoded)


def _parameter(params: RequestParams | Mapping[str, object], name: str) -> object:
    """Read either decoded protocol structs or an unknown method's raw mapping."""
    if isinstance(params, Mapping):
        return params.get(name)
    return getattr(params, "meta" if name == "_meta" else name, None)


def _argument(arguments: object, path: tuple[str, ...]) -> object:
    """Read the exact compiled property path without interpreting dotted keys."""
    value = arguments
    for name in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(name)
    return value


def _matches_integer(header: str, value: object) -> bool:
    """Compare safe JSON integers numerically, accepting equivalent 42.0 values."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float) and (
        not math.isfinite(value) or not value.is_integer()
    ):
        return False
    if abs(value) > _SAFE_INTEGER or _NUMBER.fullmatch(header) is None:
        return False
    try:
        return Decimal(header) == value
    except DecimalException:
        return False


def _matches_value(binding: HeaderBinding, header: str, value: object) -> bool:
    """Compare mirrored parameters without coercing booleans into integers."""
    if binding.kind == "integer":
        return _matches_integer(header, value)
    if binding.kind == "boolean":
        return isinstance(value, bool) and header == ("true" if value else "false")
    return isinstance(value, str) and header == value


def _validate_binding(
    headers: Headers,
    binding: HeaderBinding,
    arguments: object,
) -> None:
    """Require mirrored values precisely when their argument is present and non-null."""
    value = _argument(arguments, binding.path)
    if value is None:
        if headers.count(binding.name):
            raise _mismatch(binding.name)
        return
    header = _single_header(headers, binding.name, encoded=True)
    if not _matches_value(binding, header, value):
        raise _mismatch(binding.name)


def _validate_standard(
    headers: Headers,
    name: str,
    expected: object,
    *,
    encoded: bool = False,
) -> None:
    """Compare one required standard header with its corresponding body field."""
    if _single_header(headers, name, encoded=encoded) != expected:
        raise _mismatch(name)


def _validate_version(headers: Headers, metadata: object) -> None:
    """Distinguish invalid body metadata from a missing or disagreeing header."""
    name = "mcp-protocol-version"
    header = _single_header(headers, name)
    version = metadata.get(PROTOCOL_VERSION) if isinstance(metadata, Mapping) else None
    if not isinstance(version, str):
        raise McpInvalidParams
    if header != version:
        raise _mismatch(name)


def validate_headers(
    headers: Headers,
    envelope: JsonRpcRequest,
    params: RequestParams | Mapping[str, object] | None = None,
    bindings: tuple[HeaderBinding, ...] = (),
) -> None:
    """Enforce mirrored request metadata before protocol method dispatch.

    Unknown methods may omit ``params`` here to decode only their raw mapping.
    Notifications have no metadata-header requirements in this protocol revision.
    """
    if envelope.id is msgspec.UNSET:
        return
    if params is None:
        raw: object = msgspec.json.decode(envelope.params)
        params = raw if isinstance(raw, Mapping) else {}
    metadata = _parameter(params, "_meta")
    _validate_version(headers, metadata)
    _validate_standard(headers, "mcp-method", envelope.method)
    if envelope.method in _NAMED_METHODS:
        name = _parameter(
            params,
            "uri" if envelope.method == "resources/read" else "name",
        )
        _validate_standard(headers, "mcp-name", name, encoded=True)
    if envelope.method == "tools/call":
        arguments = _parameter(params, "arguments")
        for binding in bindings:
            _validate_binding(headers, binding, arguments)
