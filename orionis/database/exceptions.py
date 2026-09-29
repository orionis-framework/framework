from __future__ import annotations

class DatabaseException(Exception):
    """Base exception for all database-related errors."""

class ConnectionNotFoundException(DatabaseException):
    """Raised when a connection name is not present in the configuration."""

class MigrationNotFoundException(DatabaseException):
    """Raised when a recorded migration has no matching migration file."""

class MissingDatabaseDependencyException(DatabaseException):
    """Raised when a driver requires an optional package that is not installed."""

class QueryException(DatabaseException):
    """Raised when a statement fails to compile or execute."""

class TransactionException(DatabaseException):
    """Raised when transaction control methods are used incorrectly."""

class UnsupportedDriverException(DatabaseException):
    """Raised when a connection references a driver with no implementation."""
