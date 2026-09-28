from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator
    from orionis.database.contracts.connection import IConnection

_MIGRATION_CONNECTION: ContextVar[IConnection | None] = ContextVar(
    "orionis_migration_connection", default=None,
)

def current_migration_connection() -> IConnection | None:
    """
    Return the connection selected by the current migration step.

    Returns
    -------
    IConnection or None
        Connection inherited by unqualified schema and ORM operations.
    """
    return _MIGRATION_CONNECTION.get()

@contextmanager
def migration_connection_scope(connection: IConnection) -> Generator[None]:
    """
    Bind unqualified migration operations to their tracking transaction.

    Parameters
    ----------
    connection : IConnection
        Connection selected by the migration runner.

    Yields
    ------
    None
        The previous binding is restored when the step finishes or fails.
    """
    token = _MIGRATION_CONNECTION.set(connection)
    try:
        yield
    finally:
        _MIGRATION_CONNECTION.reset(token)
