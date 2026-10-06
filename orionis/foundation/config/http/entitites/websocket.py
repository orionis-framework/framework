from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import validate_integer, validate_string
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class HTTPWebSocket(BaseEntity):
    """
    Configure connection admission, inbound messages and browser origins.

    Read environment defaults when each instance is created. Explicit constructor
    values take precedence. Copy list inputs to a tuple, lowercase each origin and
    remove trailing slashes before retaining the immutable configuration.

    Attributes
    ----------
    max_connections : int
        Maximum active connections per kernel.
        Defaults to 128 from ``WEBSOCKET_MAX_CONNECTIONS``.
    max_message_size : int
        Maximum complete inbound message bytes.
        Defaults to 1 MiB from ``WEBSOCKET_MAX_MESSAGE_SIZE``.
    allow_origins : tuple[str, ...]
        Additional allowed browser origins. Empty allows the same origin only.
        The wildcard ``"*"`` explicitly allows every origin. Defaults to an empty
        tuple from the shared ``CORS_ALLOW_ORIGINS`` environment variable.
    """

    max_connections: int = field(
        default_factory=lambda: Env.get("WEBSOCKET_MAX_CONNECTIONS", 128),
        metadata={
            "description": "Maximum active WebSocket connections per kernel.",
            "default": 128,
        },
    )

    max_message_size: int = field(
        default_factory=lambda: Env.get("WEBSOCKET_MAX_MESSAGE_SIZE", 1024 * 1024),
        metadata={
            "description": "Maximum complete inbound WebSocket message bytes.",
            "default": 1024 * 1024,
        },
    )

    allow_origins: tuple[str, ...] = field(
        default_factory=lambda: Env.get("CORS_ALLOW_ORIGINS", ()),
        metadata={
            "description": (
                "Additional allowed browser origins; empty allows the same origin "
                "only, while '*' allows every origin."
            ),
            "default": (),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate limits and copy the configured origin collection.

        Returns
        -------
        None
            Freeze the validated configuration.

        Raises
        ------
        TypeError
            If limits or origin entries have invalid types.
        ValueError
            If a limit is nonpositive or an origin is empty.
        """
        super().__post_init__()
        for name in ("max_connections", "max_message_size"):
            validate_integer(getattr(self, name), name, minimum=1)
        if not isinstance(self.allow_origins, (list, tuple)):
            error_msg = "allow_origins must be a list or tuple of origin strings"
            raise TypeError(error_msg)
        for origin in self.allow_origins:
            validate_string(origin, "allow_origins")
        object.__setattr__(
            self, "allow_origins",
            tuple(origin.lower().rstrip("/") for origin in self.allow_origins),
        )
