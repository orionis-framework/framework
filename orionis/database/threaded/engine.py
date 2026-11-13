# ruff: noqa: TC002, TC003
# Keep native engine and iterator annotations available to runtime reflection.
"""Expose asynchronous checkouts without claiming a blocking driver is async."""

from __future__ import annotations
from contextlib import asynccontextmanager
from sqlalchemy.exc import SQLAlchemyError
from orionis.database.exceptions import QueryException
from orionis.database.threaded.connection import ThreadedConnection
from orionis.database.threaded.worker import (
    ThreadedWorker,
    _complete_cleanup,
    _rollback_or_invalidate,
)

from collections.abc import AsyncIterator
from sqlalchemy.engine import Engine


class ThreadedEngine:
    """Expose asynchronous checkouts without claiming a blocking driver is async."""

    __slots__ = ("_name", "sync_engine")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, engine: Engine, name: str = "redshift") -> None:
        """
        Retain a lazy blocking engine without opening any connections.

        Parameters
        ----------
        engine : ``sqlalchemy.engine.Engine``
            Blocking Core engine backed by the official connector dialect.
        name : str, optional
            Connection name used in sanitized opening errors.

        Returns
        -------
        None
            No return value.
        """
        self.sync_engine = engine
        """Blocking Core engine backed by the official connector dialect."""
        self._name = name
        """Connection name used in sanitized opening errors."""

    async def connect(self) -> ThreadedConnection:
        """
        Open one checkout without blocking the event loop.

        Returns
        -------
        orionis.database.threaded.connection.ThreadedConnection
            Connection owning a worker until it closes.

        Raises
        ------
        orionis.database.QueryException
            If the connector cannot open the connection; driver details are omitted.
        """
        try:
            return await ThreadedConnection.open(self.sync_engine)
        except SQLAlchemyError as error:
            message = (  # NOSONAR(S1110) - Preserve multiline grouping.
                f"Unable to open connection '{self._name}' ({type(error).__name__})."
            )
            raise QueryException(message) from None

    @asynccontextmanager
    async def begin(self) -> AsyncIterator[ThreadedConnection]:
        """
        Own a checkout and commit or roll back before returning it to the pool.

        Yields
        ------
        orionis.database.threaded.connection.ThreadedConnection
            Checkout with an active root transaction.
        """
        connection = await self.connect()
        primary: BaseException | None = None
        try:
            try:
                transaction = await connection.begin()
                try:
                    yield connection
                except BaseException as error:
                    await _complete_cleanup(
                        _rollback_or_invalidate(
                            transaction.rollback(),
                            connection.invalidate,
                        ),
                        error,
                    )
                    raise
                else:
                    await transaction.commit()
            except BaseException as error:
                primary = error
                if isinstance(error, SQLAlchemyError):
                    await _complete_cleanup(connection.invalidate(), error)
                raise
            finally:
                await _complete_cleanup(connection.close(), primary)
        except SQLAlchemyError as error:
            message = (  # NOSONAR(S1110) - Preserve multiline grouping.
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
            No return value.
        """
        worker = ThreadedWorker()
        primary: BaseException | None = None
        try:
            try:
                await worker.run(self.sync_engine.dispose)
            except BaseException as error:
                primary = error
                raise
            finally:
                await _complete_cleanup(worker.close(), primary)
        except SQLAlchemyError as error:
            message = (  # NOSONAR(S1110) - Preserve multiline grouping.
                f"Unable to dispose connection '{self._name}' ({type(error).__name__})."
            )
            raise QueryException(message) from None
