# ruff: noqa: TC001, TC002
# Keep worker and native transaction annotations available at runtime.
"""Settle a Core transaction on its connection's reserved worker."""

from __future__ import annotations
from sqlalchemy.engine import Transaction
from orionis.database.threaded.worker import ThreadedWorker


class ThreadedTransaction:
    """Settle a Core transaction on its connection's reserved worker."""

    __slots__ = ("_transaction", "_worker")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self,
        transaction: Transaction,
        worker: ThreadedWorker,
    ) -> None:
        """
        Retain the Core transaction and its owning worker.

        Parameters
        ----------
        transaction : ``sqlalchemy.engine.Transaction``
            Open Core transaction.
        worker : orionis.database.threaded.worker.ThreadedWorker
            Worker owning the associated DBAPI checkout.

        Returns
        -------
        None
            No return value.
        """
        self._transaction = transaction
        """Open Core transaction."""
        self._worker = worker
        """Worker owning the associated DBAPI checkout."""

    async def commit(self) -> None:
        """Commit before allowing the connection to return to the pool.

        Returns
        -------
        None
            No return value.
        """
        await self._worker.run(self._transaction.commit)

    async def rollback(self) -> None:
        """Roll back before allowing the connection to return to the pool.

        Returns
        -------
        None
            No return value.
        """
        await self._worker.run(self._transaction.rollback)
