# ruff: noqa: ANN401, SLF001, TC003
# Retain parent connection ownership, dynamic results, and runtime annotations.
"""Base class for every query builder bound to a parent model instance."""

import orionis.orm as _orm
from contextvars import ContextVar
from typing import Any
from orionis.orm.contracts.relation import IRelation
from orionis.orm.query.builder import ModelQueryBuilder
from orionis.support.types.collection import Collection

from collections.abc import Callable, Generator


class _ConstraintScope:
    """Limit inherited constraint suppression to its owner's active callback."""

    __slots__ = ("active",)
    """Reserve the active lifetime flag without a per-instance dictionary."""

    def __init__(self) -> None:
        """Start an active suppression scope.

        Returns
        -------
        None
            No return value.
        """
        self.active = True
        """Indicate whether the owning callback is still executing."""


_CONSTRAINTS: ContextVar[_ConstraintScope | None] = ContextVar(
    "orm_relation_constraints",
    default=None,
)
"""Context-local scope whose lifetime also applies to inherited contexts."""


class Relation[TRelated: _orm.Model](ModelQueryBuilder[TRelated], IRelation):
    """
    Base class for every query builder bound to a parent model instance.

    A relationship is a regular :class:`orionis.orm.query.ModelQueryBuilder` targeting
    the
    related model, pre-constrained to the rows belonging to a specific
    parent instance. Concrete kinds (``hasOne``, ``hasMany``,
    ``belongsTo``, ``belongsToMany``, and future polymorphic or
    through-relations) only need to implement the template methods
    below; the full fluent query API is inherited for free.
    """

    __slots__ = ("_eager_keys_empty", "_parent")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, parent: _orm.Model, related: type[TRelated]) -> None:
        """
        Bind a relationship query builder to its parent instance.

        Parameters
        ----------
        parent : orionis.orm.Model
            Model instance the relationship is accessed from.
        related : type of orionis.orm.Model
            Model class the relationship targets.

        Returns
        -------
        None
            No return value.
        """
        super().__init__(related)
        if related.__meta__.connection is None:
            self._resolved_connection = parent._read_connection
            """Retain the connection that owns the parent model's loaded state."""
            self._connection_name = type(parent).__meta__.connection
            """Use the parent's configured connection for an unbound related model."""
        self._parent = parent
        """Model instance the relationship is accessed from."""
        self._eager_keys_empty = False
        """Eager keys empty flag used by ``Relation``."""
        scope = _CONSTRAINTS.get()
        if scope is None or not scope.active:
            self.addConstraints()

    # ── Template methods (overridden per relationship kind) ─────────────────

    def addConstraints(self) -> None:
        """
        Constrain the query to the bound parent instance.

        Returns
        -------
        None
            No return value.
        """
        error_msg = f"{type(self).__name__} must implement addConstraints()."
        raise NotImplementedError(error_msg)

    def addEagerConstraints(self, models: list[_orm.Model]) -> None:
        """
        Constrain the query to every parent instance of an eager batch.

        Parameters
        ----------
        models : list of orionis.orm.Model
            Parent instances being eager loaded together.

        Returns
        -------
        None
            No return value.
        """
        error_msg = f"{type(self).__name__} must implement addEagerConstraints()."
        raise NotImplementedError(error_msg)

    async def getResults(self) -> Any:
        """
        Execute the relationship query for its bound parent instance.

        Returns
        -------
        typing.Any
            A single model, ``None``, or a ``Collection``, depending on
            the relationship kind.
        """
        error_msg = f"{type(self).__name__} must implement getResults()."
        raise NotImplementedError(error_msg)

    async def getEager(self) -> Collection:
        """
        Execute the relationship query assembled for eager loading.

        The default implementation reuses the regular ``get()``
        terminal, since most relationships project every matching row
        the same way whether they are lazy or eager loaded.

        Returns
        -------
        orionis.support.types.Collection
            Every related row across the whole eager-loaded batch.
        """
        if self._eager_keys_empty:
            return Collection()
        return await self.get()

    def match(
        self,
        models: list[_orm.Model],
        results: Collection,
        name: str,
    ) -> None:
        """
        Group eager-loaded results and attach them to their parents.

        Parameters
        ----------
        models : list of orionis.orm.Model
            Parent instances being eager loaded together.
        results : orionis.support.types.Collection
            Rows produced by :meth:`orionis.orm.relations.Relation.getEager`.
        name : str
            Relationship name the results are stored under.

        Returns
        -------
        None
            No return value.
        """
        error_msg = f"{type(self).__name__} must implement match()."
        raise NotImplementedError(error_msg)

    # ── Ergonomics ────────────────────────────────────────────────────────

    def __await__(self) -> Generator[Any, None, Any]:
        """
        Allow ``await`` directly on a relationship without a terminal.

        Equivalent to ``await relation.getResults()``, mirroring how
        Eloquent resolves ``$model->relation`` as a property access.

        Returns
        -------
        collections.abc.Generator
            Delegate generator driving
            :meth:`orionis.orm.relations.Relation.getResults`.
        """
        return self.getResults().__await__()

    @classmethod
    def noConstraints(
        cls,
        callback: Callable[[], Relation[Any]],
    ) -> Relation[Any]:
        """
        Build a relationship instance without its single-parent constraint.

        Used by eager loading to read a relationship's metadata (related
        model, foreign key, ...) from a sample instance without binding
        the query to that specific instance. The setting is isolated to
        the current execution context, including across worker threads.
        Inherited child contexts stop suppressing constraints when the owning
        callback returns or raises.

        Parameters
        ----------
        callback : collections.abc.Callable
            Zero-argument callable constructing the relationship,
            typically a bound relationship method such as
            ``model.posts``.

        Returns
        -------
        orionis.orm.relations.Relation
            The relationship built by ``callback``, unconstrained.
        """
        scope = _ConstraintScope()
        token = _CONSTRAINTS.set(scope)
        try:
            return callback()
        finally:
            scope.active = False
            _CONSTRAINTS.reset(token)
