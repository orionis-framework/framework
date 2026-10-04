"""Notification bus boundary for future distributed implementations."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from orionis.mcp.protocol.requests import SubscriptionFilter


class IMcpEventBus(ABC):
    """Publish server changes without retaining identities or requests."""

    __slots__ = ()

    @abstractmethod
    def listen(
        self,
        server: type,
        filters: SubscriptionFilter,
    ) -> AsyncIterator[tuple[str, str | None]]:
        """Open a bounded subscription, releasing it on iterator close."""

    @abstractmethod
    async def publish(self, server: type, method: str, uri: str | None = None) -> None:
        """Publish a notification kind to the corresponding server."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Wake subscribers for a graceful end."""
