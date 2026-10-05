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
        """
        Open a bounded subscription, releasing it on iterator close.

        Parameters
        ----------
        server : type
            Value supplied for ``server``.
        filters : SubscriptionFilter
            Value supplied for ``filters``.

        Returns
        -------
        AsyncIterator[tuple[str, str | None]]
            Result of the operation described above.
        """

    @abstractmethod
    async def publish(self, server: type, method: str, uri: str | None = None) -> None:
        """
        Publish a notification kind to the corresponding server.

        Parameters
        ----------
        server : type
            Value supplied for ``server``.
        method : str
            Value supplied for ``method``.
        uri : str | None
            Value supplied for ``uri``.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Wake subscribers for a graceful end.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
