from __future__ import annotations
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl
import msgspec.json as _msgspec_json
import msgspec.msgpack as _msgspec_msgpack
from defusedxml.ElementTree import fromstring as _xml_fromstring

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element as XMLElement

def _split_header_parameters( # NOSONAR
    header: str, *, quote_chars: str = '"',
) -> list[str]:
    """
    Split header segments at semicolons outside quoted parameter values.

    Quotes open only at the first non-whitespace character after the first
    equals sign in a segment. Escaped characters cannot close a quoted value.
    Segments retain their whitespace, quotes and escapes for the caller.
    An unterminated quoted value consumes the remainder of the header.

    Parameters
    ----------
    header : str
        Header or parameter text to split.
    quote_chars : str, optional
        Characters that may delimit a quoted value; double quotes by default.

    Returns
    -------
    list[str]
        Original segments, excluding their separating semicolons.
    """
    parts: list[str] = []
    start = 0
    quote: str | None = None
    escaped = False
    value_started: bool | None = None
    for position, char in enumerate(header):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char == ";":
            parts.append(header[start:position])
            start = position + 1
            value_started = None
        elif value_started is None and char == "=":
            value_started = False
        elif value_started is False and not char.isspace():
            value_started = True
            if char in quote_chars:
                quote = char
    parts.append(header[start:])
    return parts

def parse_content_type(header: str) -> tuple[str, dict[str, str]]:
    """
    Parse a ``Content-Type`` header into a media-type and parameter dict.

    Semicolons inside double-quoted parameter values are preserved.

    Parameters
    ----------
    header : str
        Raw ``Content-Type`` value, e.g.
        ``"multipart/form-data; boundary=----WebKit"``.

    Returns
    -------
    tuple[str, dict[str, str]]
        ``(media_type, params)`` where *media_type* is lowercase and
        *params* maps lowercase parameter names to unquoted values.
    """
    # Handle a media type without parameters.
    sc = header.find(";")
    if sc == -1:
        return header.strip().lower(), {}
    # Isolate the bare media type before the first semicolon.
    media_type = header[:sc].strip().lower()
    params: dict[str, str] = {}
    # Extract parameters without splitting semicolons inside quoted values.
    for part in _split_header_parameters(header[sc + 1 :]):
        if "=" in part:
            key, _, value = part.strip().partition("=")
            params[key.strip().lower()] = value.strip().strip('"')
    return media_type, params

def parse_json(raw: bytes) -> object:
    """
    Decode a JSON payload using ``msgspec``.

    Parameters
    ----------
    raw : bytes
        Raw JSON bytes.

    Returns
    -------
    object
        Decoded Python object (dict, list, str, int, float, bool,
        or None).

    Raises
    ------
    msgspec.DecodeError
        If *raw* is not valid JSON.
    """
    # Decode the JSON bytes into a Python value.
    return _msgspec_json.decode(raw)

def parse_msgpack(raw: bytes) -> object:
    """
    Decode a MessagePack payload using ``msgspec``.

    Parameters
    ----------
    raw : bytes
        Raw MessagePack bytes.

    Returns
    -------
    object
        Decoded Python object.

    Raises
    ------
    msgspec.DecodeError
        If *raw* is not valid MessagePack.
    """
    # Decode the MessagePack bytes into a Python value.
    return _msgspec_msgpack.decode(raw)

def parse_urlencoded(raw: bytes) -> dict[str, str]:
    """
    Decode an ``application/x-www-form-urlencoded`` payload.

    Parameters
    ----------
    raw : bytes
        URL-encoded bytes.

    Returns
    -------
    dict[str, str]
        Parsed key-value pairs; blank values are preserved.
    """
    # keep_blank_values=True retains fields submitted with empty values.
    return dict(parse_qsl(raw.decode("utf-8"), keep_blank_values=True))

def parse_urlencoded_multi(raw: bytes) -> dict[str, str | list[str]]:
    """
    Decode a URL-encoded payload, preserving duplicate-key semantics.

    A key that appears once yields a plain string value.  A key that
    appears more than once yields a list of strings in insertion order.

    Parameters
    ----------
    raw : bytes
        URL-encoded bytes.

    Returns
    -------
    dict[str, str | list[str]]
        Parsed fields where single occurrences are scalars and repeated
        occurrences are lists.
    """
    result: dict[str, str | list[str]] = {}
    # Accumulate values and promote scalars to lists on duplicate keys.
    for k, v in parse_qsl(raw.decode("utf-8"), keep_blank_values=True):
        if k in result:
            existing = result[k]
            # Append to list or promote scalar to a two-element list.
            if isinstance(existing, list):
                existing.append(v)
            else:
                result[k] = [existing, v]
        else:
            result[k] = v
    return result

def parse_xml(raw: bytes) -> XMLElement:
    """
    Parse an XML payload with entity declarations disabled.

    Uses ``defusedxml`` to reject internal and external entity declarations.
    DTDs without entity declarations are allowed; external resources are
    not resolved.

    Parameters
    ----------
    raw : bytes
        Raw XML bytes.

    Returns
    -------
    xml.etree.ElementTree.Element
        Root element of the parsed document.

    Raises
    ------
    xml.etree.ElementTree.ParseError
        If *raw* is malformed XML.
    defusedxml.common.EntitiesForbidden
        If the document declares an internal or external entity. This is a
        subclass of ``defusedxml.common.DefusedXmlException``, not ParseError.
    """
    # Defaults forbid entities and external access, but allow DTD declarations.
    return _xml_fromstring(raw)

def parse_text(raw: bytes) -> str:
    """
    Decode a UTF-8 text payload.

    Parameters
    ----------
    raw : bytes
        Raw body bytes.

    Returns
    -------
    str
        UTF-8 decoded string.
    """
    # Strict UTF-8; raises UnicodeDecodeError on invalid byte sequences.
    return raw.decode("utf-8")

def parse_binary(raw: bytes) -> bytes:
    """
    Return a binary payload unchanged.

    Parameters
    ----------
    raw : bytes
        Raw body bytes.

    Returns
    -------
    bytes
        The same bytes object, unmodified.
    """
    # Return the original binary payload.
    return raw
