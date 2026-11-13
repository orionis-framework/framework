"""Group the database components and public imports."""

from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.database.compiler import SQLCompiler
    from orionis.database.connection import Connection
    from orionis.database.connection_manager import ConnectionManager
    from orionis.database.contracts.migration import Migration
    from orionis.database.exceptions import (
        ConnectionNotFoundException,
        DatabaseException,
        MigrationNotFoundException,
        MissingDatabaseDependencyException,
        QueryException,
        TransactionException,
        UnsupportedDriverException,
    )
    from orionis.database.migrations.migrator import Migrator
    from orionis.database.seeders.events import SeederEvents
    from orionis.database.seeders.runner import SeederRunner
    from orionis.database.seeders.seeder import Seeder
    from orionis.database.transaction import Transaction

__all__ = [
    "Connection",
    "ConnectionManager",
    "ConnectionNotFoundException",
    "DatabaseException",
    "Migration",
    "MigrationNotFoundException",
    "Migrator",
    "MissingDatabaseDependencyException",
    "QueryException",
    "SQLCompiler",
    "Seeder",
    "SeederEvents",
    "SeederRunner",
    "Transaction",
    "TransactionException",
    "UnsupportedDriverException",
]

_EXCEPTIONS_MODULE = "orionis.database.exceptions"
"""Module defining the exported database exception types."""

_EXPORTS = {
    "Connection": ("orionis.database.connection", "Connection"),
    "ConnectionManager": ("orionis.database.connection_manager", "ConnectionManager"),
    "ConnectionNotFoundException": (
        _EXCEPTIONS_MODULE,
        "ConnectionNotFoundException",
    ),
    "DatabaseException": (_EXCEPTIONS_MODULE, "DatabaseException"),
    "Migration": ("orionis.database.contracts.migration", "Migration"),
    "MigrationNotFoundException": (
        _EXCEPTIONS_MODULE,
        "MigrationNotFoundException",
    ),
    "Migrator": ("orionis.database.migrations.migrator", "Migrator"),
    "MissingDatabaseDependencyException": (
        _EXCEPTIONS_MODULE,
        "MissingDatabaseDependencyException",
    ),
    "QueryException": (_EXCEPTIONS_MODULE, "QueryException"),
    "SQLCompiler": ("orionis.database.compiler", "SQLCompiler"),
    "Seeder": ("orionis.database.seeders.seeder", "Seeder"),
    "SeederEvents": ("orionis.database.seeders.events", "SeederEvents"),
    "SeederRunner": ("orionis.database.seeders.runner", "SeederRunner"),
    "Transaction": ("orionis.database.transaction", "Transaction"),
    "TransactionException": (_EXCEPTIONS_MODULE, "TransactionException"),
    "UnsupportedDriverException": (
        _EXCEPTIONS_MODULE,
        "UnsupportedDriverException",
    ),
}
"""Public export names mapped to their defining modules and attributes."""


def __getattr__(name: str) -> object:
    """
    Resolve and cache a public package export.

    Parameters
    ----------
    name : str
        Public attribute requested from this package.

    Returns
    -------
    object
        Exported object from its defining module.

    Raises
    ------
    AttributeError
        If the requested attribute is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)


def __dir__() -> list[str]:
    """
    List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
