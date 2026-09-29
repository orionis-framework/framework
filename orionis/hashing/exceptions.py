class HashException(Exception):
    """Base exception for every failure raised by the hashing module."""

class HashConfigurationException(HashException):
    """Raised when a hashing driver receives invalid cost parameters."""

class HashDriverNotSupportedException(HashException):
    """Raised when the configured hashing driver has no implementation."""

class MissingHashDependencyException(HashException):
    """Raised when the backend package of a hashing driver is missing."""
