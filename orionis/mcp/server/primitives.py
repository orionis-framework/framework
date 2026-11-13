# ruff: noqa: TC003
# Public primitive metadata is consumed through runtime type reflection.
"""Provide mcp server operations.

Includes ``Primitive``, ``Tool``, ``Resource``, ``Prompt``.
"""

from types import MappingProxyType
from collections.abc import Mapping
from typing import ClassVar
from orionis.mcp.protocol.metadata import (
    CacheHint,
    ContentAnnotations,
    Icon,
    PromptArgument,
    ToolAnnotations,
)


class Primitive:
    """Static metadata shared by tools, resources and prompts."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    name: ClassVar[str] = ""
    """Name identifier: ``''``."""
    title: ClassVar[str] = ""
    """Title identifier: ``''``."""
    description: ClassVar[str] = ""
    """Description identifier: ``''``."""
    icons: ClassVar[tuple[Icon, ...]] = ()
    """Icon metadata advertised for the primitive or server."""
    meta: ClassVar[Mapping[str, object]] = MappingProxyType({})
    """Meta produced by ``MappingProxyType``."""
    cache: ClassVar[CacheHint] = CacheHint()
    """Cache policy or cached state used by this component."""


class Tool[InputType = object, OutputType = object](Primitive):
    """Declare a typed input, optional typed output, and an injectable handle method."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    input: ClassVar[object] = None
    """Structured input supplied to the tool invocation."""
    output: ClassVar[object] = None
    """Declared schema for structured tool output."""
    annotations: ClassVar[ToolAnnotations | None] = None
    """Declared metadata describing behavior or validation types."""


class Resource(Primitive):
    """Read a declared URI or RFC 6570 template without implicit file access."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    uri: ClassVar[str] = ""
    """Uri identifier: ``''``."""
    uri_template: ClassVar[str] = ""
    """Uri template identifier: ``''``."""
    mime_type: ClassVar[str] = "text/plain"
    """Mime type identifier: ``text/plain``."""
    size: ClassVar[int | None] = None
    """Declared size of the resource content."""
    annotations: ClassVar[ContentAnnotations | None] = None
    """Declared metadata describing behavior or validation types."""


class Prompt(Primitive):
    """Declare string arguments and return user/assistant prompt messages."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    arguments: ClassVar[tuple[PromptArgument, ...]] = ()
    """Command-line argument declarations accepted by this command."""


class Server:
    """Define a server independently of any connection or transport."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    name: ClassVar[str] = ""
    """Name identifier: ``''``."""
    version: ClassVar[str] = "1.0.0"
    """Version identifier: ``1.0.0``."""
    title: ClassVar[str] = ""
    """Title identifier: ``''``."""
    description: ClassVar[str] = ""
    """Description identifier: ``''``."""
    website_url: ClassVar[str] = ""
    """Website url identifier: ``''``."""
    instructions: ClassVar[str] = ""
    """Instructions identifier: ``''``."""
    icons: ClassVar[tuple[Icon, ...]] = ()
    """Icon metadata advertised for the primitive or server."""
    tools: ClassVar[tuple[object, ...]] = ()
    """Tool declarations available through this server or catalog."""
    resources: ClassVar[tuple[type[Resource], ...]] = ()
    """Resource declarations available through this server."""
    prompts: ClassVar[tuple[type[Prompt], ...]] = ()
    """Prompt declarations available through this server."""
    extensions: ClassVar[tuple[object, ...]] = ()
    """Extensions registered for this server or transport."""
    cache: ClassVar[CacheHint] = CacheHint()
    """Cache policy or cached state used by this component."""
    list_changed: ClassVar[bool] = False
    """List changed flag used by ``Server``."""
    resource_subscriptions: ClassVar[bool] = False
    """Resource subscriptions flag used by ``Server``."""
