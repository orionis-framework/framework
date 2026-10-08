from __future__ import annotations
from functools import partial
from typing import TYPE_CHECKING, Any, Self
from orionis.database.threaded.result import ThreadedResult
from orionis.database.threaded.transaction import ThreadedTransaction
from orionis.database.threaded.worker import ThreadedWorker

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from sqlalchemy.engine import Connection, Engine
    from sqlalchemy.sql.expression import Executable

class ThreadedConnection:
    """Execute one Core checkout and buffer its results on a reserved thread."""

    __slots__ = ("_closed", "_connection", "_worker")

    def __init__(self, connection: Connection, worker: ThreadedWorker) -> None:
        """Retain an open Core connection and the worker that opened it.

        Parameters
        ----------
        connection : Connection
            Open blocking Core connection.
        worker : ThreadedWorker
            Worker reserved for this checkout.

        Returns
        -------
        None
            Initialize the connection adapter without additional I/O.
        """
        self._connection = connection
        self._worker = worker
        self._closed = False

    @classmethod
    async def open(cls, engine: Engine) -> Self:
        """Open a checkout and release late resources if the caller is cancelled.

        Parameters
        ----------
        engine : Engine
            Blocking engine supplying the checkout.

        Returns
        -------
        Self
            Connection with an independently reserved worker.
        """
        worker = ThreadedWorker()
        try:
            connection = await worker.run(
                engine.connect, on_cancel=lambda raw: raw.close(),
            )
        except BaseException:
            await worker.close()
            raise
        return cls(connection, worker)

    async def begin(self) -> ThreadedTransaction:
        """Begin a root transaction on the reserved worker.

        Returns
        -------
        ThreadedTransaction
            Transaction adapter retaining the same worker.
        """
        transaction = await self._worker.run(
            self._connection.begin, on_cancel=lambda opened: opened.rollback(),
        )
        return ThreadedTransaction(transaction, self._worker)

    async def execute(
        self,
        statement: Executable,
        parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    ) -> ThreadedResult:
        """Execute and materialize a statement entirely outside the event loop.

        Parameters
        ----------
        statement : Executable
            Compiled Core statement or parameterized textual query.
        parameters : Mapping | Sequence[Mapping] | None, optional
            Bindings for one statement or a batch.

        Returns
        -------
        ThreadedResult
            Memory-only result safe to consume after checkout release.
        """
        return await self._worker.run(partial(self._execute, statement, parameters))

    def _execute(
        self,
        statement: Executable,
        parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
    ) -> ThreadedResult:
        """Consume the live cursor before the worker completes its operation.

        Parameters
        ----------
        statement : Executable
            Core statement to execute.
        parameters : Mapping | Sequence[Mapping] | None
            Statement or batch bindings.

        Returns
        -------
        ThreadedResult
            Fully buffered rows and result metadata.
        """
        return ThreadedResult(self._connection.execute(statement, parameters))

    async def runSync[T](
        self, callback: Callable[..., T], *args: object, **kwargs: object,
    ) -> T:
        """Execute a Core schema callback on the connection's reserved worker.

        Parameters
        ----------
        callback : Callable[..., T]
            Callback receiving the blocking Core connection first.
        *args : object
            Additional callback arguments.
        **kwargs : object
            Additional callback options.

        Returns
        -------
        T
            Callback result after the blocking work completes.
        """
        return await self._worker.run(partial(
            callback, self._connection, *args, **kwargs,
        ))

    async def close(self) -> None:
        """Return the checkout and join its worker, including during cancellation.

        Returns
        -------
        None
            Complete rollback, pool release and thread shutdown.
        """
        if self._closed:
            return
        self._closed = True
        try:
            await self._worker.run(self._connection.close)
        finally:
            await self._worker.close()

    async def invalidate(self) -> None:
        """
        Discard a connection whose transaction could not be settled.

        Returns
        -------
        None
            Close the DBAPI handle on its worker instead of returning it for reuse.
        """
        await self._worker.run(self._connection.invalidate)
