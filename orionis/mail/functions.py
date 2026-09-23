from collections.abc import Mapping
from string import ascii_letters, digits
from types import MappingProxyType
from unicodedata import category
from orionis.mail.exceptions import (
    MailAttachmentException,
    MailCompositionException,
)

# Characters allowed by RFC 2045 in a MIME type or subtype token.
_TOKEN_CHARS = frozenset(ascii_letters + digits + "!#$%&'*+-.^_`|~")

# Unicode categories rejected in headers: controls, formatting, surrogates,
# and line or paragraph separators.
_HEADER_CONTROLS = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp"})

_MEDIA_TYPE_PARTS = 2
_MAX_REASON_LENGTH = 512

def header_value(value: str, label: str) -> str:
    """
    Validate a single unstructured header value.

    Parameters
    ----------
    value : str
        Header text, including an intentionally empty subject.
    label : str
        Public field name used in diagnostics.

    Returns
    -------
    str
        The unchanged safe value.

    Raises
    ------
    MailCompositionException
        If the value is not text or contains control characters.
    """
    if not isinstance(value, str) or any(
        category(char) in _HEADER_CONTROLS for char in value
    ):
        error_msg = f"{label} must be text without control characters."
        raise MailCompositionException(error_msg)
    return value

def attachment_name(value: str) -> str:
    """
    Validate the visible basename of an attachment.

    Parameters
    ----------
    value : str
        Name exposed in the Content-Disposition header.

    Returns
    -------
    str
        The validated name.

    Raises
    ------
    MailAttachmentException
        If the name is empty, unsafe, or contains a path.
    """
    try:
        header_value(value, "Attachment name")
    except MailCompositionException as exc:
        error_msg = "Attachment names must not contain control characters."
        raise MailAttachmentException(error_msg) from exc

    # Reject directory traversal and any separator that would expose a path.
    if (
        not value.strip()
        or value in {".", ".."}
        or any(char in value for char in "/\\:")
    ):
        error_msg = "Attachment names must be non-empty basenames, not paths."
        raise MailAttachmentException(error_msg)
    return value

def media_type(value: str) -> str:
    """
    Validate a bare MIME type without header parameters.

    Parameters
    ----------
    value : str
        Explicit or storage-provided MIME type.

    Returns
    -------
    str
        A lowercase type/subtype pair.

    Raises
    ------
    MailAttachmentException
        If either token is invalid or parameters are present.
    """
    parts = value.split("/") if isinstance(value, str) else []
    if len(parts) != _MEDIA_TYPE_PARTS or any(
        not part or not _TOKEN_CHARS.issuperset(part) for part in parts
    ):
        error_msg = "Attachment MIME types must contain only a type/subtype pair."
        raise MailAttachmentException(error_msg)
    return value.lower()

def freeze_owned(value: object, active: frozenset[int] = frozenset()) -> object:
    """
    Snapshot containers without copying arbitrary user objects.

    Parameters
    ----------
    value : object
        A container tree or an opaque context value.
    active : frozenset[int]
        Ancestors used to reject cyclic container structures.

    Returns
    -------
    object
        Read-only copied containers; opaque values retain identity.

    Raises
    ------
    MailCompositionException
        If a container cycle prevents an immutable snapshot.
    """
    # Values that are not owned containers are shared by reference, so
    # services and other user objects keep their identity.
    if not isinstance(value, (Mapping, list, tuple, set, frozenset)):
        return value

    if id(value) in active:
        error_msg = "Mail container structures must not contain cycles."
        raise MailCompositionException(error_msg)

    ancestors = active | {id(value)}
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: freeze_owned(item, ancestors) for key, item in value.items()},
        )
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze_owned(item, ancestors) for item in value)
    return tuple(freeze_owned(item, ancestors) for item in value)

def sanitize_reason(value: str | bytes, sensitive: tuple[str, ...] = ()) -> str:
    """
    Remove controls and configured secrets from a transport diagnostic.

    Parameters
    ----------
    value : str | bytes
        Server response, decoded with replacement when needed.
    sensitive : tuple[str, ...]
        Credentials and credential-bearing URL representations to redact.

    Returns
    -------
    str
        A bounded single-line diagnostic.
    """
    text = value.decode("utf-8", "replace") if isinstance(value, bytes) else value

    # Redact the longest secrets first so a shorter one never splits them.
    for secret in sorted(filter(None, sensitive), key=len, reverse=True):
        text = text.replace(secret, "[redacted]")

    return "".join(
        " " if category(char) in _HEADER_CONTROLS else char for char in text
    )[:_MAX_REASON_LENGTH]
