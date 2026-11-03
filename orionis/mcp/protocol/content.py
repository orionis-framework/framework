"""Provide mcp protocol operations.

Includes ``Annotations``, ``Content``, ``TextContent``, ``ImageContent``.
"""

from typing import Literal
import msgspec

# Protocol fields retain the official MCP property names.
# ruff: noqa: N815

class Annotations(msgspec.Struct, frozen=True, kw_only=True):
    """Optional audience, priority and modification hints."""

    audience: tuple[Literal["user", "assistant"], ...] | msgspec.UnsetType = (
        msgspec.UNSET
    )
    priority: float | msgspec.UnsetType = msgspec.UNSET
    lastModified: str | msgspec.UnsetType = msgspec.UNSET

class Content(msgspec.Struct, frozen=True, kw_only=True):
    """Common content metadata."""

    meta: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="_meta",
        default=msgspec.UNSET,
    )
    """Meta produced by ``msgspec.field``."""
    annotations: Annotations | msgspec.UnsetType = msgspec.UNSET

class TextContent(Content, tag="text", kw_only=True, frozen=True):
    """UTF-8 text content."""

    text: str
    """Text content carried by this protocol value."""

class ImageContent(Content, tag="image", kw_only=True, frozen=True):
    """Base64-encoded image content."""

    data: str
    """Decoded content carried by this message or request."""
    mimeType: str
    """Media type of the encoded image content."""

class AudioContent(Content, tag="audio", kw_only=True, frozen=True):
    """Base64-encoded audio content."""

    data: str
    """Decoded content carried by this message or request."""
    mimeType: str
    """Media type of the encoded audio content."""

class TextResourceContents(msgspec.Struct, frozen=True, kw_only=True):
    """Text at an explicit resource URI."""

    uri: str
    """Resource URI identifying the requested or returned content."""
    text: str
    """Text content carried by this protocol value."""
    mimeType: str | msgspec.UnsetType = msgspec.UNSET
    meta: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="_meta",
        default=msgspec.UNSET,
    )
    """Meta produced by ``msgspec.field``."""

class BlobResourceContents(msgspec.Struct, frozen=True, kw_only=True):
    """Binary resource encoded once as base64."""

    uri: str
    """Resource URI identifying the requested or returned content."""
    blob: str
    """Base64-encoded binary resource content."""
    mimeType: str | msgspec.UnsetType = msgspec.UNSET
    meta: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="_meta",
        default=msgspec.UNSET,
    )
    """Meta produced by ``msgspec.field``."""

class EmbeddedResource(Content, tag="resource", kw_only=True, frozen=True):
    """A resource embedded in tool or prompt content."""

    resource: TextResourceContents | BlobResourceContents
    """Embedded resource contents included in the response."""

class ResourceLink(Content, tag="resource_link", kw_only=True, frozen=True):
    """A discoverable resource reference, without reading its bytes."""

    name: str
    """Name identifying this declaration within its containing registry."""
    uri: str
    """Resource URI identifying the requested or returned content."""
    title: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType = msgspec.UNSET
    mimeType: str | msgspec.UnsetType = msgspec.UNSET
    size: int | msgspec.UnsetType = msgspec.UNSET
    icons: tuple[dict[str, object], ...] | msgspec.UnsetType = msgspec.UNSET

type ContentBlock = (
    TextContent | ImageContent | AudioContent | EmbeddedResource | ResourceLink
)
"""
Type alias for ``TextContent | ImageContent | AudioContent | EmbeddedResource |
ResourceLink``.
"""

class PromptMessage(msgspec.Struct, frozen=True):
    """One prompt message with a protocol-defined role."""

    role: Literal["user", "assistant"]
    """Role assigned to this message in the conversation."""
    content: ContentBlock
    """Content blocks carried by this protocol value."""
