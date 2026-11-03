"""Declare negotiated capabilities and extension-owned method/schema hooks."""

from dataclasses import dataclass, field
from types import MappingProxyType
from orionis.mcp.context import freeze_json
from orionis.mcp.protocol.metavalidation import validate_meta_key
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import msgspec
    from collections.abc import Callable, Mapping

@dataclass(frozen=True, slots=True, kw_only=True)
class McpExtension:
    """Declare negotiated capabilities and extension-owned method/schema hooks."""

    identifier: str
    """Unique identifier used to negotiate the extension."""
    capabilities: Mapping[str, object] = field(default_factory=dict)
    """Capabilities advertised by the compiled server."""
    methods: Mapping[str, Callable[..., object]] = field(default_factory=dict)
    """Methods produced by ``field``."""
    decoders: Mapping[str, msgspec.json.Decoder] = field(default_factory=dict)
    """Decoders produced by ``field``."""
    schema_hook: Callable[[dict[str, object]], None] | None = None
    """Hook that contributes extension-specific schema definitions."""

    def __post_init__(self) -> None:
        """
        Detach declarations so a compiled server cannot change accidentally.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        validate_meta_key(self.identifier, extension=True)
        object.__setattr__(self, "capabilities", freeze_json(self.capabilities))
        object.__setattr__(self, "methods", MappingProxyType(dict(self.methods)))
        object.__setattr__(self, "decoders", MappingProxyType(dict(self.decoders)))
