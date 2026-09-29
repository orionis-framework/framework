from __future__ import annotations

class StorageException(Exception):
    """Base exception for all storage-related errors."""

class DiskNotFoundException(StorageException):
    """Raised when a disk is not defined in the filesystems configuration."""

class DriverNotSupportedException(StorageException):
    """Raised when a disk references a driver without an implementation."""

class MissingStorageDependencyException(StorageException):
    """Raised when a driver requires an optional package that is not installed."""

class StoragePathException(StorageException):
    """Raised when a storage path is malformed or escapes the disk root."""

class StorageFileNotFoundException(StorageException):
    """Raised when a file does not exist on the target disk."""

class UnsupportedStorageOperationException(StorageException):
    """Raised when a driver cannot perform the requested operation."""
