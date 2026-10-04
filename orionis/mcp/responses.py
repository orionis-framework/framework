"""Transport-independent response factories for Orionis primitives."""

import base64
from dataclasses import dataclass, field, replace
import math
from typing import TYPE_CHECKING, Literal, Self

import msgspec

from orionis.mcp.protocol.content import (
    Annotations,
    AudioContent,
    BlobResourceContents,
    ContentBlock,
    EmbeddedResource,
    ImageContent,
    ResourceLink,
    TextContent,
    TextResourceContents,
)
from orionis.mcp.protocol.metavalidation import validate_metadata
from orionis.mcp.protocol.validation import validate_json

if TYPE_CHECKING:
    from orionis.mcp.protocol.metadata import ContentAnnotations


@dataclass(frozen=True, slots=True)
class Progress:
    """A request-scoped progress update awaiting a client-provided token."""

    current: float
    total: float | None = None
    message: str | None = None


@dataclass(frozen=True, slots=True)
class McpResponse:
    """Compose protocol content without knowing the transport or DI container."""

    content: tuple[ContentBlock, ...] = ()
    structured_content: object = msgspec.UNSET
    is_error: bool = False
    role: Literal["user", "assistant"] = "user"
    progress_update: Progress | None = None
    meta: dict[str, object] = field(default_factory=dict)

    @classmethod
    def text(cls, value: str) -> Self:
        """Return text content."""
        return cls(content=(TextContent(text=value),))

    @classmethod
    def image(cls, value: bytes, mime_type: str) -> Self:
        """Encode raw image bytes once."""
        return cls(
            content=(
                ImageContent(
                    data=base64.b64encode(value).decode("ascii"),
                    mimeType=mime_type,
                ),
            ),
        )

    @classmethod
    def audio(cls, value: bytes, mime_type: str) -> Self:
        """Encode raw audio bytes once."""
        return cls(
            content=(
                AudioContent(
                    data=base64.b64encode(value).decode("ascii"),
                    mimeType=mime_type,
                ),
            ),
        )

    @classmethod
    def resource(
        cls,
        uri: str,
        value: str | bytes,
        mime_type: str | None = None,
    ) -> Self:
        """Embed text or binary resource content at an explicit URI."""
        mime = mime_type if mime_type is not None else msgspec.UNSET
        contents = (
            TextResourceContents(uri=uri, text=value, mimeType=mime)
            if isinstance(value, str)
            else BlobResourceContents(
                uri=uri,
                blob=base64.b64encode(value).decode("ascii"),
                mimeType=mime,
            )
        )
        return cls(content=(EmbeddedResource(resource=contents),))

    @classmethod
    def resourceLink(
        cls,
        uri: str,
        name: str,
        *,
        title: str | None = None,
        description: str | None = None,
        mime_type: str | None = None,
    ) -> Self:
        """Link to a resource without loading it."""
        return cls(
            content=(
                ResourceLink(
                    uri=uri,
                    name=name,
                    title=title if title is not None else msgspec.UNSET,
                    description=description
                    if description is not None
                    else msgspec.UNSET,
                    mimeType=mime_type if mime_type is not None else msgspec.UNSET,
                ),
            ),
        )

    @classmethod
    def structured(cls, value: object) -> Self:
        """Return any JSON value and the recommended serialized text content."""
        validate_json(value)
        encoded = msgspec.json.encode(value)
        return cls(
            content=(TextContent(text=encoded.decode("utf-8")),),
            structured_content=msgspec.json.decode(encoded),
        )

    @classmethod
    def error(cls, message: str) -> Self:
        """Return an application-visible tool error, with an explicit safe message."""
        return cls(content=(TextContent(text=message),), is_error=True)

    @classmethod
    def progress(
        cls,
        current: float,
        total: float | None = None,
        message: str | None = None,
    ) -> Self:
        """Yield progress; the dispatcher suppresses it without client opt-in."""
        if type(current) not in (int, float) or not math.isfinite(current) or (
            total is not None
            and (type(total) not in (int, float) or not math.isfinite(total))
        ):
            error = "Progress values must be finite"
            raise ValueError(error)
        return cls(progress_update=Progress(current, total, message))

    def asAssistant(self) -> Self:
        """Assign the assistant role for a prompt response."""
        return replace(self, role="assistant")

    def asUser(self) -> Self:
        """Assign the user role for a prompt response."""
        return replace(self, role="user")

    def withMeta(self, metadata: dict[str, object]) -> Self:
        """Attach result metadata without allowing reserved protocol keys."""
        validate_metadata(metadata, allow_reserved=False)
        validate_json(metadata)
        return replace(self, meta={**self.meta, **metadata})

    def withContentMeta(self, metadata: dict[str, object]) -> Self:
        """Attach application metadata to each content block."""
        validate_metadata(metadata, allow_reserved=False)
        validate_json(metadata)
        return replace(
            self,
            content=tuple(
                msgspec.structs.replace(
                    part,
                    meta={
                        **({} if part.meta is msgspec.UNSET else part.meta),
                        **metadata,
                    },
                )
                for part in self.content
            ),
        )

    def withAnnotations(self, annotations: ContentAnnotations) -> Self:
        """Set audience, priority and modification hints on content blocks."""
        value = msgspec.convert(msgspec.to_builtins(annotations), type=Annotations)
        return replace(
            self,
            content=tuple(
                msgspec.structs.replace(part, annotations=value)
                for part in self.content
            ),
        )
