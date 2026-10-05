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
    capabilities: Mapping[str, object] = field(default_factory=dict)
    methods: Mapping[str, Callable[..., object]] = field(default_factory=dict)
    decoders: Mapping[str, msgspec.json.Decoder] = field(default_factory=dict)
    schema_hook: Callable[[dict[str, object]], None] | None = None

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
