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
_NUMBER = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?\Z", re.ASCII)
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
    """
    Locate annotations even inside unsupported schema constructs.

    Parameters
    ----------
    value : object
        Value to inspect, transform or validate.

    Returns
    -------
    bool
        Result of the operation described above.
    """
    if isinstance(value, Mapping):
        return _ANNOTATION in value or any(
            _contains_annotation(child) for child in value.values()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_annotation(child) for child in value)
    return False

def _binding(schema: Mapping[str, object], path: tuple[str, ...]) -> HeaderBinding:
    """
    Validate the name and primitive type at one reachable property.

    Parameters
    ----------
    schema : Mapping[str, object]
        Schema declaration used for conversion and validation.
    path : tuple[str, ...]
        Value supplied for ``path``.

    Returns
    -------
    HeaderBinding
        Result of the operation described above.
    """
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
    """
    Visit properties chains and reject annotations hidden elsewhere.

    Parameters
    ----------
    schema : Mapping[str, object]
        Schema declaration used for conversion and validation.
    path : tuple[str, ...]
        Value supplied for ``path``.
    bindings : list[HeaderBinding]
        Declared bindings associated with this operation.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    for key, value in schema.items():
        if key == _ANNOTATION:
            if path:
                bindings.append(_binding(schema, path))
                continue
            message = "x-mcp-header is only valid on statically reachable properties"
            raise ValueError(message)
        if key == "properties" and isinstance(value, Mapping):
            _walk_properties(value, path, bindings)
        elif _contains_annotation(value):
            message = "x-mcp-header cannot occur outside a properties chain"
            raise ValueError(message)

def _walk_properties(
    properties: Mapping[str, object],
    path: tuple[str, ...],
    bindings: list[HeaderBinding],
) -> None:
    """
    Visit named object properties with statically known extraction paths.

    Parameters
    ----------
    properties : Mapping[str, object]
        Named child schemas.
    path : tuple[str, ...]
        Parent property path.
    bindings : list[HeaderBinding]
        Accumulator for mirrored header declarations.

    Returns
    -------
    None
        Valid child mappings have been visited in declaration order.
    """
    for name, child in properties.items():
        if isinstance(name, str) and isinstance(child, Mapping):
            _walk_schema(child, (*path, name), bindings)

def compile_header_bindings(
    input_schema: Mapping[str, object],
) -> tuple[HeaderBinding, ...]:
    """
    Validate tool schema annotations once and freeze extraction paths.

    Parameters
    ----------
    input_schema : Mapping[str, object]
        Value supplied for ``input_schema``.

    Returns
    -------
    tuple[HeaderBinding, ...]
        Result of the operation described above.
    """
    bindings: list[HeaderBinding] = []
    _walk_schema(input_schema, (), bindings)
    names = {binding.name for binding in bindings}
    if len(names) != len(bindings):
        message = "x-mcp-header names must be case-insensitively unique"
        raise ValueError(message)
    return tuple(bindings)

def _mismatch(name: str) -> McpProtocolException:
    """
    Report the failing header without reflecting untrusted field values.

    Parameters
    ----------
    name : str
        Value supplied for ``name``.

    Returns
    -------
    McpProtocolException
        Result of the operation described above.
    """
    return McpProtocolException(-32020, f"Header mismatch: {name}", status=400)

def _decode_value(value: str, name: str, *, encoded: bool) -> str:
    """
    Validate ASCII transport syntax and decode the exact Base64 sentinel.

    Parameters
    ----------
    value : str
        Value to inspect, transform or validate.
    name : str
        Value supplied for ``name``.
    encoded : bool
        Value supplied for ``encoded``.

    Returns
    -------
    str
        Result of the operation described above.
    """
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
    """
    Require one field occurrence, including case-insensitive duplicates.

    Parameters
    ----------
    headers : Headers
        Value supplied for ``headers``.
    name : str
        Value supplied for ``name``.
    encoded : bool
        Value supplied for ``encoded``.

    Returns
    -------
    str
        Result of the operation described above.
    """
    if headers.count(name) != 1:
        raise _mismatch(name)
    value = headers.get(name)
    if value is None:
        raise _mismatch(name)
    return _decode_value(value, name, encoded=encoded)

def _parameter(params: RequestParams | Mapping[str, object], name: str) -> object:
    """
    Read either decoded protocol structs or an unknown method's raw mapping.

    Parameters
    ----------
    params : RequestParams | Mapping[str, object]
        Parameters decoded for the requested operation.
    name : str
        Value supplied for ``name``.

    Returns
    -------
    object
        Result of the operation described above.
    """
    if isinstance(params, Mapping):
        return params.get(name)
    return getattr(params, "meta" if name == "_meta" else name, None)

def _argument(arguments: object, path: tuple[str, ...]) -> object:
    """
    Read the exact compiled property path without interpreting dotted keys.

    Parameters
    ----------
    arguments : object
        Arguments supplied for this operation.
    path : tuple[str, ...]
        Value supplied for ``path``.

    Returns
    -------
    object
        Result of the operation described above.
    """
    value = arguments
    for name in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(name)
    return value

def _matches_integer(header: str, value: object) -> bool:
    """
    Compare safe JSON integers numerically, accepting equivalent 42.0 values.

    Parameters
    ----------
    header : str
        Value supplied for ``header``.
    value : object
        Value to inspect, transform or validate.

    Returns
    -------
    bool
        Result of the operation described above.
    """
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
    """
    Compare mirrored parameters without coercing booleans into integers.

    Parameters
    ----------
    binding : HeaderBinding
        Value supplied for ``binding``.
    header : str
        Value supplied for ``header``.
    value : object
        Value to inspect, transform or validate.

    Returns
    -------
    bool
        Result of the operation described above.
    """
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
    """
    Require mirrored values precisely when their argument is present and non-null.

    Parameters
    ----------
    headers : Headers
        Value supplied for ``headers``.
    binding : HeaderBinding
        Value supplied for ``binding``.
    arguments : object
        Arguments supplied for this operation.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
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
    """
    Compare one required standard header with its corresponding body field.

    Parameters
    ----------
    headers : Headers
        Value supplied for ``headers``.
    name : str
        Value supplied for ``name``.
    expected : object
        Value supplied for ``expected``.
    encoded : bool
        Value supplied for ``encoded``.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    if _single_header(headers, name, encoded=encoded) != expected:
        raise _mismatch(name)

def _validate_version(headers: Headers, metadata: object) -> None:
    """
    Distinguish invalid body metadata from a missing or disagreeing header.

    Parameters
    ----------
    headers : Headers
        Value supplied for ``headers``.
    metadata : object
        Metadata associated with the current operation.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
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
    """
    Enforce mirrored request metadata before protocol method dispatch.

    Unknown methods may omit ``params`` here to decode only their raw mapping.
    Notifications have no metadata-header requirements in this protocol revision.

    Parameters
    ----------
    headers : Headers
        Value supplied for ``headers``.
    envelope : JsonRpcRequest
        Value supplied for ``envelope``.
    params : RequestParams | Mapping[str, object] | None
        Parameters decoded for the requested operation.
    bindings : tuple[HeaderBinding, ...]
        Declared bindings associated with this operation.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
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
