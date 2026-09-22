from __future__ import annotations
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl
import msgspec.json as _msgspec_json
import msgspec.msgpack as _msgspec_msgpack
from defusedxml.ElementTree import fromstring as _xml_fromstring

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element as XMLElement

def parse_content_type(header: str) -> tuple[str, dict[str, str]]:
    """
    Parse a ``Content-Type`` header into a media-type and parameter dict.

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
    # Walk each semicolon-delimited segment and extract key=value pairs.
    for part in header[sc + 1 :].split(";"):
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
    Parse an XML payload safely, preventing XXE and DTD attacks.

    Uses ``defusedxml`` to reject external entity references and DTD
    expansions before they are evaluated.

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
        If *raw* is malformed or contains forbidden constructs.
    """
    # defusedxml.fromstring blocks XXE/DTD before any content is parsed.
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
