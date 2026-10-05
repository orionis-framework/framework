from typing import Literal
import msgspec

class CacheHint(msgspec.Struct, frozen=True, kw_only=True):
    """Describe client cache freshness without caching server-side results."""

    ttl_ms: int = msgspec.field(name="ttlMs", default=0)
    scope: Literal["public", "private"] = msgspec.field(
        name="cacheScope",
        default="private",
    )

    def __post_init__(self) -> None:
        """
        Reject cache hints with an invalid TTL or scope.

        Returns
        -------
        None
            Validate the cache TTL and scope during initialization.

        Raises
        ------
        ValueError
            If the TTL is negative or not an integer, or the scope is invalid.
        """
        if type(self.ttl_ms) is not int or self.ttl_ms < 0:
            message = "Cache TTL must be a nonnegative integer."
            raise ValueError(message)
        if self.scope not in ("public", "private"):
            message = "Cache scope must be public or private."
            raise ValueError(message)

CacheHints = CacheHint

class Icon(msgspec.Struct, frozen=True, kw_only=True, omit_defaults=True):
    """An icon reference; the server never fetches its source."""

    src: str
    mime_type: str | msgspec.UnsetType = msgspec.field(
        name="mimeType",
        default=msgspec.UNSET,
    )
    sizes: tuple[str, ...] | msgspec.UnsetType = msgspec.UNSET
    theme: Literal["light", "dark"] | msgspec.UnsetType = msgspec.UNSET

    def __post_init__(self) -> None:
        """
        Reject icon sources that do not use HTTPS or a data URI.

        Returns
        -------
        None
            Validate the icon source during initialization.

        Raises
        ------
        ValueError
            If the source is not a string or uses an unsupported scheme.
        """
        if not isinstance(self.src, str) or not self.src.startswith(
            ("https://", "data:"),
        ):
            message = "MCP icon sources must use HTTPS or data URIs."
            raise ValueError(message)

class ToolAnnotations(msgspec.Struct, frozen=True, kw_only=True, omit_defaults=True):
    """Describe tool behavior as hints, never as authorization rules."""

    title: str | msgspec.UnsetType = msgspec.UNSET
    read_only: bool | msgspec.UnsetType = msgspec.field(
        name="readOnlyHint",
        default=msgspec.UNSET,
    )
    destructive: bool | msgspec.UnsetType = msgspec.field(
        name="destructiveHint",
        default=msgspec.UNSET,
    )
    idempotent: bool | msgspec.UnsetType = msgspec.field(
        name="idempotentHint",
        default=msgspec.UNSET,
    )
    open_world: bool | msgspec.UnsetType = msgspec.field(
        name="openWorldHint",
        default=msgspec.UNSET,
    )

class ContentAnnotations(msgspec.Struct, frozen=True, kw_only=True, omit_defaults=True):
    """Resource/content audience, relevance, and modification hints."""

    audience: tuple[Literal["user", "assistant"], ...] | msgspec.UnsetType = (
        msgspec.UNSET
    )
    priority: float | msgspec.UnsetType = msgspec.UNSET
    last_modified: str | msgspec.UnsetType = msgspec.field(
        name="lastModified",
        default=msgspec.UNSET,
    )

    def __post_init__(self) -> None:
        """
        Keep content priority within the inclusive protocol interval.

        Returns
        -------
        None
            Validate the priority when it is set.

        Raises
        ------
        ValueError
            If the priority is outside the range from zero to one.
        """
        if self.priority is not msgspec.UNSET and not 0 <= self.priority <= 1:
            message = "Content priority must be between zero and one."
            raise ValueError(message)

class PromptArgument(msgspec.Struct, frozen=True, kw_only=True, omit_defaults=True):
    """Declare one string-valued prompt argument."""

    name: str
    title: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType = msgspec.UNSET
    required: bool = False

class ServerInfo(msgspec.Struct, frozen=True, kw_only=True, omit_defaults=True):
    """Describe one compiled server implementation."""

    name: str
    version: str
    title: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType = msgspec.UNSET
    website_url: str | msgspec.UnsetType = msgspec.field(
        name="websiteUrl",
        default=msgspec.UNSET,
    )
    icons: tuple[Icon, ...] | msgspec.UnsetType = msgspec.UNSET

class PrimitiveMetadata(msgspec.Struct, frozen=True, kw_only=True):
    """Common typed fields used to validate static registry metadata at boot."""

    name: str
    title: str | msgspec.UnsetType = msgspec.UNSET
    description: str | msgspec.UnsetType = msgspec.UNSET
    icons: tuple[Icon, ...] | msgspec.UnsetType = msgspec.UNSET
    meta: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="_meta", default=msgspec.UNSET,
    )

class ToolMetadata(PrimitiveMetadata, frozen=True, kw_only=True):
    """A native tool schema with optional behavioral hints."""

    input_schema: dict[str, object] = msgspec.field(name="inputSchema")
    output_schema: dict[str, object] | msgspec.UnsetType = msgspec.field(
        name="outputSchema", default=msgspec.UNSET,
    )
    annotations: ToolAnnotations | msgspec.UnsetType = msgspec.UNSET

class ResourceMetadata(PrimitiveMetadata, frozen=True, kw_only=True):
    """A resource or template already validated by the URI compiler."""

    uri: str | msgspec.UnsetType = msgspec.UNSET
    uri_template: str | msgspec.UnsetType = msgspec.field(
        name="uriTemplate", default=msgspec.UNSET,
    )
    mime_type: str | msgspec.UnsetType = msgspec.field(
        name="mimeType", default=msgspec.UNSET,
    )
    size: int | msgspec.UnsetType = msgspec.UNSET
    annotations: ContentAnnotations | msgspec.UnsetType = msgspec.UNSET

class PromptMetadata(PrimitiveMetadata, frozen=True, kw_only=True):
    """Prompt descriptors and their string-valued argument declarations."""

    arguments: tuple[PromptArgument, ...] | msgspec.UnsetType = msgspec.UNSET
