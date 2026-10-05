from types import MappingProxyType
from typing import ClassVar, TYPE_CHECKING
from orionis.mcp.protocol.metadata import (
    CacheHint,
    ContentAnnotations,
    Icon,
    PromptArgument,
    ToolAnnotations,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

class Primitive:
    """Static metadata shared by tools, resources and prompts."""

    __slots__ = ()

    name: ClassVar[str] = ""
    title: ClassVar[str] = ""
    description: ClassVar[str] = ""
    icons: ClassVar[tuple[Icon, ...]] = ()
    meta: ClassVar[Mapping[str, object]] = MappingProxyType({})
    cache: ClassVar[CacheHint] = CacheHint()

class Tool[InputType = object, OutputType = object](Primitive):
    """Declare a typed input, optional typed output, and an injectable handle method."""

    __slots__ = ()

    input: ClassVar[object] = None
    output: ClassVar[object] = None
    annotations: ClassVar[ToolAnnotations | None] = None

class Resource(Primitive):
    """Read a declared URI or RFC 6570 template without implicit file access."""

    __slots__ = ()

    uri: ClassVar[str] = ""
    uri_template: ClassVar[str] = ""
    mime_type: ClassVar[str] = "text/plain"
    size: ClassVar[int | None] = None
    annotations: ClassVar[ContentAnnotations | None] = None

class Prompt(Primitive):
    """Declare string arguments and return user/assistant prompt messages."""

    __slots__ = ()

    arguments: ClassVar[tuple[PromptArgument, ...]] = ()

class Server:
    """Define a server independently of any connection or transport."""

    __slots__ = ()

    name: ClassVar[str] = ""
    version: ClassVar[str] = "1.0.0"
    title: ClassVar[str] = ""
    description: ClassVar[str] = ""
    website_url: ClassVar[str] = ""
    instructions: ClassVar[str] = ""
    icons: ClassVar[tuple[Icon, ...]] = ()
    tools: ClassVar[tuple[object, ...]] = ()
    resources: ClassVar[tuple[type[Resource], ...]] = ()
    prompts: ClassVar[tuple[type[Prompt], ...]] = ()
    extensions: ClassVar[tuple[object, ...]] = ()
    cache: ClassVar[CacheHint] = CacheHint()
    list_changed: ClassVar[bool] = False
    resource_subscriptions: ClassVar[bool] = False
