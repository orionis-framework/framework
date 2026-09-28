from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import TracebackType

class ITransaction(ABC):
    """
    Contract for a database transaction usable as an async context manager.

    Entering the context begins a transaction (or a savepoint when one is
    already active); leaving it commits on success and rolls back when an
    exception escapes the block.
    """

    __slots__ = ()

    @abstractmethod
    async def __aenter__(self) -> ITransaction:
        """
        Begin the transaction and enter the context.

        Returns
        -------
        ITransaction
            The active transaction context.

        Raises
        ------
        TransactionException
            If the transaction cannot be started.
        """

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """
        Finalize the transaction when leaving the context.

        Parameters
        ----------
        exc_type : type of BaseException or None
            Exception class raised inside the block, if any.
        exc : BaseException or None
            Exception instance raised inside the block, if any.
        traceback : TracebackType or None
            Traceback associated with the exception, if any.

        Returns
        -------
        bool
            Always ``False`` so exceptions propagate to the caller.
        """
