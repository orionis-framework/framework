from __future__ import annotations
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any
from orionis.orm.contracts.relation import IRelation
from orionis.orm.query.builder import ModelQueryBuilder
from orionis.support.types.collection import Collection

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from orionis.orm.model import Model

_CONSTRAINTS: ContextVar[bool] = ContextVar("orm_relation_constraints", default=True)

class Relation[TRelated: "Model"](ModelQueryBuilder[TRelated], IRelation):
    """
    Base class for every query builder bound to a parent model instance.

    A relationship is a regular :class:`ModelQueryBuilder` targeting the
    related model, pre-constrained to the rows belonging to a specific
    parent instance. Concrete kinds (``hasOne``, ``hasMany``,
    ``belongsTo``, ``belongsToMany``, and future polymorphic or
    through-relations) only need to implement the template methods
    below; the full fluent query API is inherited for free.
    """

    __slots__ = ("_eager_keys_empty", "_parent")

    def __init__(self, parent: Model, related: type[TRelated]) -> None:
        """
        Bind a relationship query builder to its parent instance.

        Parameters
        ----------
        parent : Model
            Model instance the relationship is accessed from.
        related : type of Model
            Model class the relationship targets.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(related)
        self._parent = parent
        self._eager_keys_empty = False
        if _CONSTRAINTS.get():
            self.addConstraints()

    # ── Template methods (overridden per relationship kind) ─────────────────

    def addConstraints(self) -> None:
        """
        Constrain the query to the bound parent instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        error_msg = f"{type(self).__name__} must implement addConstraints()."
        raise NotImplementedError(error_msg)

    def addEagerConstraints(self, models: list[Model]) -> None:
        """
        Constrain the query to every parent instance of an eager batch.

        Parameters
        ----------
        models : list of Model
            Parent instances being eager loaded together.

        Returns
        -------
        None
            This method does not return a value.
        """
        error_msg = f"{type(self).__name__} must implement addEagerConstraints()."
        raise NotImplementedError(error_msg)

    async def getResults(self) -> Any:  # noqa: ANN401
        """
        Execute the relationship query for its bound parent instance.

        Returns
        -------
        Any
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
        Collection
            Every related row across the whole eager-loaded batch.
        """
        if self._eager_keys_empty:
            return Collection()
        return await self.get()

    def match(
        self,
        models: list[Model],
        results: Collection,
        name: str,
    ) -> None:
        """
        Group eager-loaded results and attach them to their parents.

        Parameters
        ----------
        models : list of Model
            Parent instances being eager loaded together.
        results : Collection
            Rows produced by :meth:`getEager`.
        name : str
            Relationship name the results are stored under.

        Returns
        -------
        None
            This method does not return a value.
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
        Generator
            Delegate generator driving :meth:`getResults`.
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

        Parameters
        ----------
        callback : Callable
            Zero-argument callable constructing the relationship,
            typically a bound relationship method such as
            ``model.posts``.

        Returns
        -------
        Relation
            The relationship built by ``callback``, unconstrained.
        """
        token = _CONSTRAINTS.set(False)
        try:
            return callback()
        finally:
            _CONSTRAINTS.reset(token)
