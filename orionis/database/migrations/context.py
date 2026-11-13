# ruff: noqa: TC001, TC003
# Keep reflection annotations available for migration context consumers.
"""Provide database migrations operations.

Includes ``current_migration_connection``, ``migration_connection_scope``.
"""

from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Generator
from dataclasses import dataclass
from orionis.database.contracts.connection import IConnection


@dataclass(slots=True)
class _MigrationBinding:
    """Invalidate inherited connection selection when its owning scope ends."""

    connection: IConnection
    """Connection selected by the active migration or seeder."""
    active: bool = True
    """Whether the owning scope is still running."""


_MIGRATION_CONNECTION: ContextVar[_MigrationBinding | None] = ContextVar(
    "orionis_migration_connection",
    default=None,
)
"""Context-local migration connection isolated between asynchronous tasks."""


def current_migration_connection() -> IConnection | None:
    """
    Return the connection selected by the current migration step.

    Returns
    -------
    orionis.database.contracts.IConnection or None
        Connection inherited by unqualified schema and ORM operations.
    """
    binding = _MIGRATION_CONNECTION.get()
    return binding.connection if binding is not None and binding.active else None


@contextmanager
def migration_connection_scope(connection: IConnection) -> Generator[None]:
    """
    Bind unqualified migration operations to their tracking transaction.

    Parameters
    ----------
    connection : orionis.database.contracts.IConnection
        Connection selected by the migration runner.

    Yields
    ------
    None
        No yielded value. Restore the previous binding on exit and invalidate
        the completed binding in child contexts that inherited it.
    """
    binding = _MigrationBinding(connection)
    token = _MIGRATION_CONNECTION.set(binding)
    try:
        yield
    finally:
        binding.active = False
        _MIGRATION_CONNECTION.reset(token)
