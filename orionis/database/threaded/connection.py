# ruff: noqa: TC002, TC003
# Keep native checkout and callback annotations available to runtime reflection.
"""Execute one Core checkout and buffer its results on a reserved thread."""

from __future__ import annotations
import asyncio
from functools import partial
from typing import Any, Self
from orionis.database.threaded.result import ThreadedResult
from orionis.database.threaded.transaction import ThreadedTransaction
from orionis.database.threaded.worker import (
    ThreadedWorker,
    _complete_cleanup,
    _wait_for_completion,
)

from collections.abc import Callable, Mapping, Sequence
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql.expression import Executable


class ThreadedConnection:
    """Execute one Core checkout and buffer its results on a reserved thread."""

    __slots__ = ("_close_task", "_closed", "_connection", "_worker")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, connection: Connection, worker: ThreadedWorker) -> None:
        """
        Retain an open Core connection and the worker that opened it.

        Parameters
        ----------
        connection : ``sqlalchemy.engine.Connection``
            Open blocking Core connection.
        worker : orionis.database.threaded.worker.ThreadedWorker
            Worker reserved for this checkout.

        Returns
        -------
        None
            No return value.
        """
        self._connection = connection
        """Open blocking Core connection."""
        self._worker = worker
        """Worker reserved for this checkout."""
        self._closed = False
        """Whether checkout release has started or already completed."""
        self._close_task: asyncio.Task[None] | None = None
        """Shared checkout release coordinator while cleanup remains pending."""

    @classmethod
    async def open(cls, engine: Engine) -> Self:
        """
        Open a checkout and release late resources if the caller is cancelled.

        Parameters
        ----------
        engine : ``sqlalchemy.engine.Engine``
            Blocking engine supplying the checkout.

        Returns
        -------
        typing.Self
            Connection with an independently reserved worker.
        """
        worker = ThreadedWorker()
        try:
            connection = await worker.run(
                engine.connect,
                on_cancel=lambda raw: raw.close(),
            )
        except BaseException as error:
            await _complete_cleanup(worker.close(), error)
            raise
        return cls(connection, worker)

    async def begin(self) -> ThreadedTransaction:
        """
        Begin a root transaction on the reserved worker.

        Returns
        -------
        orionis.database.threaded.transaction.ThreadedTransaction
            Transaction adapter retaining the same worker.
        """
        transaction = await self._worker.run(
            self._connection.begin,
            on_cancel=lambda opened: opened.rollback(),
        )
        return ThreadedTransaction(transaction, self._worker)

    async def execute(
        self,
        statement: Executable,
        parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    ) -> ThreadedResult:
        """
        Execute and materialize a statement entirely outside the event loop.

        Parameters
        ----------
        statement : ``sqlalchemy.sql.expression.Executable``
            Compiled Core statement or parameterized textual query.
        parameters : Mapping | Sequence[Mapping] | None, optional
            Bindings for one statement or a batch.

        Returns
        -------
        orionis.database.threaded.result.ThreadedResult
            Memory-only result safe to consume after checkout release.
        """
        return await self._worker.run(partial(self._execute, statement, parameters))

    def _execute(
        self,
        statement: Executable,
        parameters: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
    ) -> ThreadedResult:
        """
        Consume the live cursor before the worker completes its operation.

        Parameters
        ----------
        statement : ``sqlalchemy.sql.expression.Executable``
            Core statement to execute.
        parameters : Mapping | Sequence[Mapping] | None
            Statement or batch bindings.

        Returns
        -------
        orionis.database.threaded.result.ThreadedResult
            Fully buffered rows and result metadata.
        """
        return ThreadedResult(self._connection.execute(statement, parameters))

    async def runSync[T](
        self,
        callback: Callable[..., T],
        *args: object,
        **kwargs: object,
    ) -> T:
        """
        Execute a Core schema callback on the connection's reserved worker.

        Parameters
        ----------
        callback : collections.abc.Callable[``...``, ``T``]
            Callback receiving the blocking Core connection first.
        *args : object
            Additional callback arguments.
        **kwargs : object
            Additional callback options.

        Returns
        -------
        ``T``
            Callback result after the blocking work completes.
        """
        return await self._worker.run(
            partial(
                callback,
                self._connection,
                *args,
                **kwargs,
            ),
        )

    async def close(self) -> None:
        """Return the checkout and join its worker, including during cancellation.

        Concurrent close callers wait for the same native release and shutdown.

        Returns
        -------
        None
            No return value.
        """
        if self._close_task is None:
            if self._closed:
                return
            self._closed = True
            release = self._release()
            try:
                self._close_task = asyncio.create_task(release)
            except BaseException:
                release.close()
                self._closed = False
                raise
            self._close_task.add_done_callback(self._closedTask)
        await _wait_for_completion(self._close_task)

    def _closedTask(self, pending: asyncio.Task[None]) -> None:
        """Release the completed coordinator and its copied execution context.

        Parameters
        ----------
        pending : asyncio.Task[None]
            Shared checkout release task that has reached a terminal state.

        Returns
        -------
        None
            No return value.
        """
        if self._close_task is pending:
            self._close_task = None

    async def _release(self) -> None:
        """Return the native checkout before joining its reserved worker.

        Returns
        -------
        None
            No return value.
        """
        primary: BaseException | None = None
        try:
            await self._worker.run(self._connection.close)
        except BaseException as error:
            primary = error
            raise
        finally:
            await _complete_cleanup(self._worker.close(), primary)

    async def invalidate(self) -> None:
        """
        Discard a connection whose transaction could not be settled.

        Returns
        -------
        None
            No return value.
        """
        await self._worker.run(self._connection.invalidate)
