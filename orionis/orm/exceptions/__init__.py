from __future__ import annotations

class OrmException(Exception):
    """Base exception for all ORM-related errors."""

class OrmConfigurationException(OrmException):
    """Raised when the ORM is used before its wiring is complete."""

class ModelNotFoundException(OrmException):
    """Raised when a model lookup that must succeed finds no records."""

class MassAssignmentException(OrmException):
    """Raised when a mass assignment violates the fillable/guarded rules."""

class InvalidQueryException(OrmException):
    """Raised when a query builder call receives invalid arguments."""

class RelationNotFoundException(OrmException):
    """Raised when a relationship name cannot be resolved on a model."""

class ScopeNotFoundException(OrmException):
    """Raised when a query scope name is not declared by the model."""

__all__ = [
    "InvalidQueryException",
    "MassAssignmentException",
    "ModelNotFoundException",
    "OrmConfigurationException",
    "OrmException",
    "RelationNotFoundException",
    "ScopeNotFoundException",
]
