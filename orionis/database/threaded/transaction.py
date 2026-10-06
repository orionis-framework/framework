from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.engine import Transaction
    from orionis.database.threaded.worker import ThreadedWorker

class ThreadedTransaction:
    """Settle a Core transaction on its connection's reserved worker."""

    __slots__ = ("_transaction", "_worker")

    def __init__(
        self, transaction: Transaction, worker: ThreadedWorker,
    ) -> None:
        """Retain the Core transaction and its owning worker.

        Parameters
        ----------
        transaction : Transaction
            Open Core transaction.
        worker : ThreadedWorker
            Worker owning the associated DBAPI checkout.

        Returns
        -------
        None
            Initialize the asynchronous transaction adapter.
        """
        self._transaction = transaction
        self._worker = worker

    async def commit(self) -> None:
        """Commit before allowing the connection to return to the pool.

        Returns
        -------
        None
            Complete the blocking commit operation.
        """
        await self._worker.run(self._transaction.commit)

    async def rollback(self) -> None:
        """Roll back before allowing the connection to return to the pool.

        Returns
        -------
        None
            Complete the blocking rollback operation.
        """
        await self._worker.run(self._transaction.rollback)
