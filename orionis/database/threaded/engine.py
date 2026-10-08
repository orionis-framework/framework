from __future__ import annotations
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING
from sqlalchemy.exc import SQLAlchemyError
from orionis.database.exceptions import QueryException
from orionis.database.threaded.connection import ThreadedConnection
from orionis.database.threaded.worker import ThreadedWorker

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from sqlalchemy.engine import Engine

class ThreadedEngine:
    """Expose asynchronous checkouts without claiming a blocking driver is async."""

    __slots__ = ("_name", "sync_engine")

    def __init__(self, engine: Engine, name: str = "redshift") -> None:
        """
        Retain a lazy blocking engine without opening any connections.

        Parameters
        ----------
        engine : Engine
            Blocking Core engine backed by the official connector dialect.
        name : str, optional
            Connection name used in sanitized opening errors.

        Returns
        -------
        None
            Initialize the adapter without starting worker threads.
        """
        self.sync_engine = engine
        self._name = name

    async def connect(self) -> ThreadedConnection:
        """
        Open one checkout without blocking the event loop.

        Returns
        -------
        ThreadedConnection
            Connection owning a worker until it closes.

        Raises
        ------
        QueryException
            If the connector cannot open the connection; driver details are omitted.
        """
        try:
            return await ThreadedConnection.open(self.sync_engine)
        except SQLAlchemyError as error:
            message = (
                f"Unable to open connection '{self._name}' "
                f"({type(error).__name__})."
            )
            raise QueryException(message) from None

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[ThreadedConnection]:
        """
        Own a checkout and commit or roll back before returning it to the pool.

        Yields
        ------
        ThreadedConnection
            Checkout with an active root transaction.
        """
        connection = await self.connect()
        try:
            try:
                transaction = await connection.begin()
                try:
                    yield connection
                except BaseException:
                    await transaction.rollback()
                    raise
                else:
                    await transaction.commit()
            except SQLAlchemyError:
                await connection.invalidate()
                raise
            finally:
                await connection.close()
        except SQLAlchemyError as error:
            message = (
                f"Unable to complete transaction on connection '{self._name}' "
                f"({type(error).__name__})."
            )
            raise QueryException(message) from None

    async def dispose(self) -> None:
        """
        Close idle pooled connections outside the event loop.

        Returns
        -------
        None
            Dispose the blocking pool and join the temporary cleanup worker.
        """
        worker = ThreadedWorker()
        try:
            try:
                await worker.run(self.sync_engine.dispose)
            finally:
                await worker.close()
        except SQLAlchemyError as error:
            message = (
                f"Unable to dispose connection '{self._name}' "
                f"({type(error).__name__})."
            )
            raise QueryException(message) from None
