"""The five content variants in the MCP 2026-07-28 schema."""

from typing import Literal

import msgspec


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
    annotations: Annotations | msgspec.UnsetType = msgspec.UNSET


class TextContent(Content, tag="text", kw_only=True, frozen=True):
    """UTF-8 text content."""

    text: str


class ImageContent(Content, tag="image", kw_only=True, frozen=True):
    """Base64-encoded image content."""

    data: str
    mimeType: str


class AudioContent(Content, tag="audio", kw_only=True, frozen=True):
    """Base64-encoded audio content."""

    data: str
    mimeType: str


class TextResourceContents(msgspec.Struct, frozen=True, kw_only=True):
    """Text at an explicit resource URI."""

    uri: str
    text: str
    mimeType: str | msgspec.UnsetType = msgspec.UNSET
    meta: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="_meta",
        default=msgspec.UNSET,
    )


class BlobResourceContents(msgspec.Struct, frozen=True, kw_only=True):
    """Binary resource encoded once as base64."""

    uri: str
    blob: str
    mimeType: str | msgspec.UnsetType = msgspec.UNSET
    meta: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="_meta",
        default=msgspec.UNSET,
    )


class EmbeddedResource(Content, tag="resource", kw_only=True, frozen=True):
    """A resource embedded in tool or prompt content."""

    resource: TextResourceContents | BlobResourceContents


class ResourceLink(Content, tag="resource_link", kw_only=True, frozen=True):
    """A discoverable resource reference, without reading its bytes."""

    name: str
    uri: str
    title: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType = msgspec.UNSET
    mimeType: str | msgspec.UnsetType = msgspec.UNSET
    size: int | msgspec.UnsetType = msgspec.UNSET
    icons: tuple[dict[str, object], ...] | msgspec.UnsetType = msgspec.UNSET


type ContentBlock = (
    TextContent | ImageContent | AudioContent | EmbeddedResource | ResourceLink
)


class PromptMessage(msgspec.Struct, frozen=True):
    """One prompt message with a protocol-defined role."""

    role: Literal["user", "assistant"]
    content: ContentBlock
