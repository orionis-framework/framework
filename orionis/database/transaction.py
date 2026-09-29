from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.database.contracts.transaction import ITransaction

if TYPE_CHECKING:
    from types import TracebackType
    from orionis.database.contracts.connection import IConnection

class Transaction(ITransaction):
    """
    Async context manager driving a connection-level transaction.

    Entering the context begins a transaction on the wrapped connection
    (a savepoint when one is already active); leaving it commits on
    success and rolls back when an exception escapes the block.
    """

    __slots__ = ("_connection",)

    def __init__(self, connection: IConnection) -> None:
        """
        Initialize the transaction around a connection.

        Parameters
        ----------
        connection : IConnection
            Connection whose transaction lifecycle is managed.

        Returns
        -------
        None
            This method does not return a value.
        """
        self._connection: IConnection = connection

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
        await self._connection.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        """
        Commit or roll back the transaction when leaving the context.

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
        # Commit on a clean exit; roll back when an exception escaped.
        if exc_type is None:
            await self._connection.commit()
        else:
            await self._connection.rollback()
        return False
