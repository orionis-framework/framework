from __future__ import annotations
from dataclasses import dataclass, field
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class HTTPWebSocket(BaseEntity):
    """
    Configure connection admission, inbound messages and browser origins.

    Attributes
    ----------
    max_connections : int
        Maximum active connections per kernel; defaults to 128.
    max_message_size : int
        Maximum complete inbound message bytes; defaults to one MiB.
    allow_origins : tuple[str, ...]
        Additional allowed browser origins. Empty allows the same origin only.
        A wildcard explicitly allows every origin.
    """

    max_connections: int = 128
    max_message_size: int = 1024 * 1024
    allow_origins: tuple[str, ...] = field(default_factory=tuple)

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
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                error_msg = f"{name} must be an integer"
                raise TypeError(error_msg)
            if value <= 0:
                error_msg = f"{name} must be positive"
                raise ValueError(error_msg)
        if not isinstance(self.allow_origins, (list, tuple)):
            error_msg = "allow_origins must be a list or tuple of origin strings"
            raise TypeError(error_msg)
        for origin in self.allow_origins:
            if not isinstance(origin, str):
                error_msg = "WebSocket origins must be strings"
                raise TypeError(error_msg)
            if not origin.strip():
                error_msg = "WebSocket origins must not be empty"
                raise ValueError(error_msg)
        object.__setattr__(
            self, "allow_origins",
            tuple(origin.lower().rstrip("/") for origin in self.allow_origins),
        )
