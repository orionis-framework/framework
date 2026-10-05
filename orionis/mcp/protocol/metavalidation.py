import re
from collections.abc import Mapping
import msgspec
from orionis.mcp.protocol.metadata import ServerInfo

_LABEL = r"[A-Za-z](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
_NAME = r"(?:[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?)?"
_META_KEY = re.compile(rf"(?:(?:{_LABEL})(?:\.{_LABEL})*/)?{_NAME}\Z")
_TRACE_PARENT = re.compile(
    r"([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})(.*)\Z",
)
_STATE_KEY = re.compile(
    r"(?:[a-z][a-z0-9_*/-]{0,255}|[a-z0-9][a-z0-9_*/-]{0,240}"
    r"@[a-z][a-z0-9_*/-]{0,13})\Z",
)
_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_MAX_TRACE_MEMBERS = 32
_MAX_TRACE_VALUE = 256

def validate_meta_key(key: str, *, extension: bool = False) -> None:
    """
    Check the specification's prefix and name grammar.

    Parameters
    ----------
    key : str
        Value supplied for ``key``.
    extension : bool
        Value supplied for ``extension``.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    if not isinstance(key, str) or not _META_KEY.fullmatch(key) or (
        extension and "/" not in key
    ):
        message = "Invalid MCP metadata key"
        raise ValueError(message)

def validate_metadata(metadata: object, *, allow_reserved: bool = True) -> None:
    """
    Preserve unknown metadata while validating its names and trace formats.

    Parameters
    ----------
    metadata : object
        Metadata associated with the current operation.
    allow_reserved : bool
        Value supplied for ``allow_reserved``.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    if not isinstance(metadata, Mapping):
        message = "MCP metadata must be an object"
        raise TypeError(message)
    for key in metadata:
        validate_meta_key(key)
        labels = key.partition("/")[0].split(".") if "/" in key else []
        if not allow_reserved and len(labels) > 1 and labels[1] in (
            "modelcontextprotocol", "mcp",
        ):
            message = "Application metadata cannot override reserved MCP keys"
            raise ValueError(message)
    for key, validator in (
        ("traceparent", _trace_parent),
        ("tracestate", _trace_state),
        ("baggage", _baggage),
    ):
        if key in metadata:
            value = metadata[key]
            if not isinstance(value, str) or not validator(value):
                message = f"Invalid W3C {key} metadata"
                raise ValueError(message)

def validate_client_capabilities(capabilities: Mapping[str, object]) -> None:
    """
    Validate known capabilities without closing the protocol's open set.

    Parameters
    ----------
    capabilities : Mapping[str, object]
        Value supplied for ``capabilities``.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    for key, children in (
        ("elicitation", ("form", "url")),
        ("sampling", ("context", "tools")),
        ("roots", ()),
        ("experimental", ()),
        ("extensions", ()),
    ):
        if key not in capabilities:
            continue
        value = capabilities[key]
        if not isinstance(value, Mapping):
            message = "Client capability must be an object"
            raise TypeError(message)
        _capability_settings(key, value, children)

def _capability_settings(
    key: str, value: Mapping[str, object], children: tuple[str, ...],
) -> None:
    """
    Validate the nested settings of a known client capability.

    Parameters
    ----------
    key : str
        Capability name.
    value : Mapping[str, object]
        Settings advertised by the client.
    children : tuple[str, ...]
        Known child settings for closed capability names.

    Returns
    -------
    None
        Nested settings and extension names have been checked.

    Raises
    ------
    ValueError
        If a setting is not a mapping or an extension name is invalid.
    """
    for name in (value if key in ("experimental", "extensions") else children):
        if name in value and not isinstance(value[name], Mapping):
            message = "Client capability settings must be an object"
            raise ValueError(message)
        if key == "extensions":
            validate_meta_key(name, extension=True)

def validate_implementation(value: object) -> None:
    """
    Check the standard client/server implementation record.

    Parameters
    ----------
    value : object
        Value to inspect, transform or validate.

    Returns
    -------
    None
        Complete the documented operation without returning a value.
    """
    msgspec.convert(value, type=ServerInfo, strict=True)

def _trace_parent(value: str) -> bool:
    """
    Accept W3C version zero and forward-compatible future versions.

    Parameters
    ----------
    value : str
        Value to inspect, transform or validate.

    Returns
    -------
    bool
        Result of the operation described above.
    """
    match = _TRACE_PARENT.fullmatch(value)
    if match is None:
        return False
    version, trace_id, parent_id, _, suffix = match.groups()
    return (
        version != "ff"
        and int(trace_id, 16) != 0
        and int(parent_id, 16) != 0
        and (not suffix if version == "00" else not suffix or suffix.startswith("-"))
    )

def _trace_state(value: str) -> bool:
    """
    Check ordered tracestate members, including unique vendor keys.

    Parameters
    ----------
    value : str
        Value to inspect, transform or validate.

    Returns
    -------
    bool
        Result of the operation described above.
    """
    members = value.split(",")
    if len(members) > _MAX_TRACE_MEMBERS:
        return False
    seen = set()
    for member in members:
        key, separator, item = member.strip(" \t").partition("=")
        if not separator:
            return False
        if not _STATE_KEY.fullmatch(key) or key in seen or (
            not item or len(item) > _MAX_TRACE_VALUE or item.endswith(" ")
            or any(char in ",=" or not " " <= char <= "~" for char in item)
        ):
            return False
        seen.add(key)
    return True

def _baggage(value: str) -> bool:
    """
    Check W3C baggage grammar without interpreting application values.

    Parameters
    ----------
    value : str
        Value to inspect, transform or validate.

    Returns
    -------
    bool
        Result of the operation described above.
    """
    if not value:
        return True
    for member in value.split(","):
        parts = member.strip(" \t").split(";")
        for index, part in enumerate(parts):
            key, separator, item = part.strip(" \t").partition("=")
            if not _TOKEN.fullmatch(key) or (index == 0 and not separator):
                return False
            if separator and any(
                char in '\\";, ' or not "!" <= char <= "~"
                for char in item.strip(" \t")
            ):
                return False
    return True
