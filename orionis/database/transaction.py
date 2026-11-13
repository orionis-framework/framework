# ruff: noqa: PLC0415, TC001, TC003
# Keep protocol and context-manager annotations available to runtime reflection.
"""Async context manager driving a connection-level transaction."""

from __future__ import annotations
from orionis.database.contracts.transaction import ITransaction
from types import TracebackType
from orionis.database.contracts.connection import IConnection
from orionis.database.threaded.worker import _diagnostic_error


class Transaction(ITransaction):
    """
    Async context manager driving a connection-level transaction.

    Entering the context begins a transaction on the wrapped connection
    (a savepoint when one is already active); leaving it commits on
    success and rolls back when an exception escapes the block.
    """

    __slots__ = ("_connection",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, connection: IConnection) -> None:
        """
        Initialize the transaction around a connection.

        Parameters
        ----------
        connection : orionis.database.contracts.IConnection
            Connection whose transaction lifecycle is managed.

        Returns
        -------
        None
            No return value.
        """
        self._connection: IConnection = connection
        """Connection whose transaction lifecycle is managed."""

    async def __aenter__(self) -> ITransaction:
        """
        Begin the transaction and enter the context.

        Returns
        -------
        orionis.database.contracts.ITransaction
            The active transaction context.

        Raises
        ------
        orionis.database.TransactionException
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

        Keep public control calls in the owning task. If the body already
        failed, report an ordinary rollback failure without replacing it.

        Parameters
        ----------
        exc_type : type of BaseException or None
            Exception class raised inside the block, if any.
        exc : BaseException or None
            Exception instance raised inside the block, if any.
        traceback : types.TracebackType or None
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
            # Public transaction control must stay in the task that owns it.
            try:
                await self._connection.rollback()
            except Exception as error:
                if exc is None:
                    raise
                from orionis.failure.runtime import capture

                await capture(
                    _diagnostic_error(error),
                    flow="database",
                    phase="cleanup",
                )
        return False
