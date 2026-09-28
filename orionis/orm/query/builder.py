from __future__ import annotations
import asyncio
import inspect
from typing import TYPE_CHECKING, Any, Self
from orionis.orm.attributes import serialize_for_storage
from orionis.orm.contracts.builder import IModelQueryBuilder
from orionis.orm.exceptions import (
    ModelNotFoundException,
    RelationNotFoundException,
    ScopeNotFoundException,
)
from orionis.orm.query.base_builder import QueryBuilderBase
from orionis.orm.query.expressions import AggregateFunction, DeletePlan
from orionis.orm.resolver import ConnectionResolver
from orionis.support.types.collection import Collection

if TYPE_CHECKING:
    from orionis.database.contracts.connection import IConnection
    from orionis.orm.collections.paginator import Paginator
    from orionis.orm.model import Model

# Default page size used by pagination.
_DEFAULT_PER_PAGE: int = 15

# Soft delete visibility modes a model query can run under.
_TRASHED_EXCLUDE: str = "exclude"
_TRASHED_INCLUDE: str = "with"
_TRASHED_ONLY: str = "only"

class ModelQueryBuilder[TModel: "Model"](QueryBuilderBase, IModelQueryBuilder):
    """
    Fluent query builder bound to a model class.

    It adds model awareness on top of :class:`QueryBuilderBase`: rows
    are hydrated into model instances, written values go through the
    declared casts, timestamps are maintained, and relationships can be
    eager loaded. The query language itself is entirely inherited, so a
    model query and a ``DB.table(...)`` query compile identically.
    """

    __slots__ = (
        "_eager_loads",
        "_meta",
        "_model",
        "_scopes_applied",
        "_trashed_mode",
        "_without_scopes",
    )

    # ruff: noqa: ANN401

    def __init__(self, model: type[TModel]) -> None:
        """
        Initialize the builder for a model class.

        Parameters
        ----------
        model : type of Model
            Model class the queries run against.

        Returns
        -------
        None
            This method does not return a value.
        """
        meta = model.__meta__
        super().__init__(meta.table)
        self._model = model
        self._meta = meta
        self._connection_name = meta.connection
        self._eager_loads: dict[str, None] = {}
        self._without_scopes: set[str] = set()
        self._trashed_mode: str = _TRASHED_EXCLUDE
        self._scopes_applied: bool = False

    def __getattr__(self, name: str) -> Any:
        """
        Expose the local scopes declared by the bound model.

        Parameters
        ----------
        name : str
            Attribute requested on the builder.

        Returns
        -------
        Any
            Callable applying the scope and returning the builder.

        Raises
        ------
        AttributeError
            If the name is neither a builder member nor a local scope.
        """
        # Reached only when normal attribute lookup already failed, so a
        # missing slot during construction must not be masked.
        if name.startswith("_"):
            error_msg = f"'{type(self).__name__}' object has no attribute '{name}'"
            raise AttributeError(error_msg)

        method = self._meta.scopes.get(name)
        if method is None:
            error_msg = f"'{type(self).__name__}' object has no attribute '{name}'"
            raise AttributeError(error_msg)

        scope = getattr(self._model, method)

        def apply(*args: Any, **kwargs: Any) -> Self:
            """
            Apply the local scope to this builder.

            Parameters
            ----------
            *args : Any
                Positional arguments forwarded to the scope.
            **kwargs : Any
                Keyword arguments forwarded to the scope.

            Returns
            -------
            ModelQueryBuilder
                The same builder, enabling fluent chaining.
            """
            scope(self, *args, **kwargs)
            return self

        return apply

    # ── Eager loading ───────────────────────────────────────────────────────

    def withRelations(self, *names: str) -> Self:
        """
        Eager load the given relationships alongside the query.

        Each relationship is loaded once in declaration order;
        :meth:`load` is an alias.

        Parameters
        ----------
        *names : str
            Relationship method names declared on the model.

        Returns
        -------
        ModelQueryBuilder
            The same builder, enabling fluent chaining.
        """
        self._eager_loads.update(dict.fromkeys(names))
        return self

    def load(self, *names: str) -> Self:
        """
        Eager load the given relationships; alias of :meth:`withRelations`.

        Parameters
        ----------
        *names : str
            Relationship method names declared on the model.

        Returns
        -------
        ModelQueryBuilder
            The same builder, enabling fluent chaining.
        """
        return self.withRelations(*names)

    # ── Scopes and soft deletes ─────────────────────────────────────────────

    def withoutGlobalScope(self, name: str) -> Self:
        """
        Disable one global scope for this query.

        Parameters
        ----------
        name : str
            Name the global scope was registered under.

        Returns
        -------
        ModelQueryBuilder
            The same builder, enabling fluent chaining.
        """
        self._without_scopes.add(name)
        return self

    def withoutGlobalScopes(self, *names: str) -> Self:
        """
        Disable several global scopes, or every one of them.

        Parameters
        ----------
        *names : str
            Scope names to disable; empty disables all of them.

        Returns
        -------
        ModelQueryBuilder
            The same builder, enabling fluent chaining.
        """
        self._without_scopes.update(names or self._meta.global_scopes)
        return self

    def scope(self, name: str, *args: Any, **kwargs: Any) -> Self:
        """
        Apply a local scope by name.

        Useful when the scope name collides with a builder method; the
        attribute form (``query.active()``) is the common one.

        Parameters
        ----------
        name : str
            Scope name, without the ``scope`` prefix.
        *args : Any
            Positional arguments forwarded to the scope.
        **kwargs : Any
            Keyword arguments forwarded to the scope.

        Returns
        -------
        ModelQueryBuilder
            The same builder, enabling fluent chaining.

        Raises
        ------
        ScopeNotFoundException
            If the model declares no such scope.
        """
        method = self._meta.scopes.get(name)
        if method is None:
            error_msg = (
                f"Model [{self._model.__name__}] declares no scope '{name}'."
            )
            raise ScopeNotFoundException(error_msg)
        getattr(self._model, method)(self, *args, **kwargs)
        return self

    def withTrashed(self) -> Self:
        """
        Include soft deleted rows in the query results.

        Returns
        -------
        ModelQueryBuilder
            The same builder, enabling fluent chaining.
        """
        self._trashed_mode = _TRASHED_INCLUDE
        return self

    def onlyTrashed(self) -> Self:
        """
        Restrict the query to soft deleted rows.

        Returns
        -------
        ModelQueryBuilder
            The same builder, enabling fluent chaining.
        """
        self._trashed_mode = _TRASHED_ONLY
        return self

    def withoutTrashed(self) -> Self:
        """
        Exclude soft deleted rows; the default behavior.

        Returns
        -------
        ModelQueryBuilder
            The same builder, enabling fluent chaining.
        """
        self._trashed_mode = _TRASHED_EXCLUDE
        return self

    async def restore(self) -> int:
        """
        Restore every soft deleted row matched by the query.

        Returns
        -------
        int
            Number of restored rows.
        """
        column = self._meta.deleted_column
        if column is None:
            return 0
        return await self.withTrashed().onlyTrashed().update({column: None})

    async def forceDelete(self) -> int:
        """
        Delete the matched rows permanently, ignoring soft deletes.

        Returns
        -------
        int
            Number of affected rows.
        """
        self._trashed_mode = _TRASHED_INCLUDE
        self._beforeExecute()
        plan = DeletePlan(
            table=self._plan.table,
            wheres=list(self._plan.wheres),
        )
        return await self._connection().delete(plan)

    async def delete(self) -> int:
        """
        Delete the matched rows, honoring soft deletes when enabled.

        Returns
        -------
        int
            Number of affected rows.
        """
        column = self._meta.deleted_column
        if column is None:
            return await super().delete()
        return await self.update({column: self._model.freshTimestamp()})

    # ── Retrieval terminals ─────────────────────────────────────────────────

    async def get(self) -> Collection:
        """
        Execute the query and hydrate every matching row.

        Returns
        -------
        Collection
            Collection of hydrated model instances.

        Raises
        ------
        QueryException
            If the statement fails to compile or execute.
        RelationNotFoundException
            If an eager-loaded relationship name does not resolve to one.
        """
        self._beforeExecute()
        rows = await self._connection().select(self._plan)
        hydrate = self._model._newFromDatabase  # noqa: SLF001
        models = [hydrate(row) for row in rows]
        await self._fireRetrieved(models)
        if self._eager_loads and models:
            await self._eagerLoad(models)
        return Collection(models)

    async def first(self) -> TModel | None:
        """
        Execute the query and hydrate only the first matching row.

        Returns
        -------
        Model or None
            First matching model, or ``None`` without matches.

        Raises
        ------
        QueryException
            If the statement fails to compile or execute.
        RelationNotFoundException
            If an eager-loaded relationship name does not resolve to one.
        """
        self._beforeExecute()
        probe = self._plan.clone()
        probe.limit_value = 1
        rows = await self._connection().select(probe)
        if not rows:
            return None
        instance = self._model._newFromDatabase(rows[0])  # noqa: SLF001
        models = [instance]
        await self._fireRetrieved(models)
        if self._eager_loads:
            await self._eagerLoad(models)
        return instance

    async def firstOrFail(self) -> TModel:
        """
        Return the first matching row or raise when none exists.

        Returns
        -------
        Model
            First matching model.

        Raises
        ------
        ModelNotFoundException
            If the query yields no rows.
        """
        instance = await self.first()
        if instance is None:
            error_msg = f"No records found for model [{self._model.__name__}]."
            raise ModelNotFoundException(error_msg)
        return instance

    async def find(self, key: Any) -> TModel | None:
        """
        Retrieve a model by its primary key.

        Parameters
        ----------
        key : Any
            Primary key value to look up.

        Returns
        -------
        Model or None
            Matching model, or ``None`` when absent.
        """
        return await self.where(self._meta.primary_key, key).first()

    async def findOrFail(self, key: Any) -> TModel:
        """
        Retrieve a model by primary key or raise when absent.

        Parameters
        ----------
        key : Any
            Primary key value to look up.

        Returns
        -------
        Model
            Matching model.

        Raises
        ------
        ModelNotFoundException
            If no record matches the key.
        """
        instance = await self.find(key)
        if instance is None:
            error_msg = (
                f"No records found for model [{self._model.__name__}] "
                f"with key [{key}]."
            )
            raise ModelNotFoundException(error_msg)
        return instance

    async def value(self, column: str) -> Any:
        """
        Return a single column value of the first matching row.

        Parameters
        ----------
        column : str
            Column whose value is returned.

        Returns
        -------
        Any
            Column value, or ``None`` without matches.
        """
        instance = await self.clone().select(column).first()
        return getattr(instance, column) if instance is not None else None

    async def pluck(self, column: str) -> Collection:
        """
        Return one column of every matching row.

        Parameters
        ----------
        column : str
            Column whose values are collected.

        Returns
        -------
        Collection
            Collection of column values.
        """
        models = await self.clone().select(column).get()
        return Collection([getattr(model, column) for model in models])

    async def paginate(
        self,
        page: int = 1,
        per_page: int = _DEFAULT_PER_PAGE,
    ) -> Paginator:
        """
        Execute the query returning a length-aware page of results.

        Parameters
        ----------
        page : int, optional
            Page number starting at 1. Defaults to the first page.
        per_page : int, optional
            Number of items per page. Defaults to 15.

        Returns
        -------
        Paginator
            Page of hydrated models with pagination metadata.

        Raises
        ------
        InvalidQueryException
            If the page or page size are not positive integers.
        """
        self.forPage(page, per_page)

        if self._connection().inTransaction():
            # A shared transactional connection cannot serve two
            # statements at once; run the count and the page in turn.
            total = int(await self._aggregate(AggregateFunction.COUNT, "*") or 0)
            items = await self.get()
        else:
            # Outside a transaction each query acquires its own pooled
            # connection, so the count and the page can run concurrently.
            count_result, items = await asyncio.gather(
                self._aggregate(AggregateFunction.COUNT, "*"),
                self.get(),
            )
            total = int(count_result or 0)

        return self._paginator(items, total, page, per_page)

    # ── Model-aware hooks ───────────────────────────────────────────────────

    def clone(self) -> Self:
        """
        Return an independent copy of this builder.

        Returns
        -------
        ModelQueryBuilder
            Detached copy carrying its own plan and eager-load list.
        """
        duplicate = super().clone()
        duplicate._eager_loads = self._eager_loads.copy()  # noqa: SLF001
        duplicate._without_scopes = set(self._without_scopes)  # noqa: SLF001
        return duplicate

    def _beforeExecute(self) -> None:
        """
        Apply the global scopes and the soft delete filter once.

        Scopes are folded into the plan at execution time, not at
        construction, so ``withoutGlobalScope`` and ``withTrashed`` can
        be called anywhere in the chain.

        Returns
        -------
        None
            This method does not return a value.
        """
        if self._scopes_applied:
            return
        self._scopes_applied = True

        for name, scope in self._meta.global_scopes.items():
            if name not in self._without_scopes:
                scope(self)

        column = self._meta.deleted_column
        if column is None:
            return
        if self._trashed_mode == _TRASHED_EXCLUDE:
            self.whereNull(column)
        elif self._trashed_mode == _TRASHED_ONLY:
            self.whereNotNull(column)

    async def _fireRetrieved(self, models: list[TModel]) -> None:
        """
        Dispatch the ``retrieved`` event for freshly hydrated models.

        Parameters
        ----------
        models : list of Model
            Models hydrated by the terminal that just ran.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Skip the whole loop when no listener is registered, which is
        # the common case on a hot hydration path.
        if not self._meta.events.get("retrieved"):
            return
        for model in models:
            await model.fireEvent("retrieved")

    def _connection(self) -> IConnection:
        """
        Resolve the database connection for the bound model.

        Returns
        -------
        IConnection
            Connection declared by the model, or the default one.
        """
        return ConnectionResolver.connection(self._connection_name)

    def _serializeValues(self, values: dict[str, Any]) -> dict[str, Any]:
        """
        Apply the model casts before values reach the database.

        Parameters
        ----------
        values : dict
            Column values to write.

        Returns
        -------
        dict
            Values converted to their storage representation.
        """
        return serialize_for_storage(self._meta, values)

    def _prepareUpdate(self, values: dict[str, Any]) -> dict[str, Any]:
        """
        Refresh the update timestamp of a mass update payload.

        Parameters
        ----------
        values : dict
            Column values to assign.

        Returns
        -------
        dict
            Payload including the refreshed update timestamp, when the
            model maintains timestamps.
        """
        updated_column = self._meta.updated_column
        if updated_column and updated_column not in values:
            values[updated_column] = self._model.freshTimestamp()
        return values

    def _existsColumns(self) -> tuple[str, ...]:
        """
        Return the projection used by existence probes.

        Returns
        -------
        tuple of str
            The primary key alone, the cheapest column to fetch.
        """
        return (self._meta.primary_key,)

    def _defaultTimestampColumn(self) -> str:
        """
        Return the column :meth:`latest` and :meth:`oldest` default to.

        Returns
        -------
        str
            Creation timestamp column when declared, primary key
            otherwise.
        """
        return self._meta.created_column or self._meta.primary_key

    # ── Internal helpers ────────────────────────────────────────────────────

    async def _eagerLoad(self, models: list[TModel]) -> None:
        """
        Resolve every pending eager-loaded relationship for a result set.

        Reads each relationship's metadata from the first model (its
        query is otherwise identical for every instance of the same
        class), constrains it to the whole batch in a single query, and
        assigns the grouped results back to each model.

        Parameters
        ----------
        models : list of Model
            Hydrated models to attach the relationships onto.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        RelationNotFoundException
            If a requested name is not a relationship method.
        """
        # Imported locally: Relation subclasses ModelQueryBuilder, so
        # importing it at module level here would cycle back through
        # orionis.orm.relations.relation.
        from orionis.orm.relations.relation import Relation  # noqa: PLC0415

        sample = models[0]
        for name in self._eager_loads:
            accessor = getattr(sample, name, None)
            if not callable(accessor):
                raise RelationNotFoundException(self._relationErrorMessage(name))

            relation = Relation.noConstraints(accessor)
            if not isinstance(relation, Relation):
                # The accessor may be an unrelated async method (e.g. a
                # typo matching `save`); close its coroutine instead of
                # leaking it, since it was never meant to be awaited.
                if inspect.iscoroutine(relation):
                    relation.close()
                raise RelationNotFoundException(self._relationErrorMessage(name))

            relation.addEagerConstraints(models)
            results = await relation.getEager()
            relation.match(models, results, name)

    def _relationErrorMessage(self, name: str) -> str:
        """
        Build the error message for an unresolvable relationship name.

        Parameters
        ----------
        name : str
            Relationship name requested for eager loading.

        Returns
        -------
        str
            Human readable error message.
        """
        return (
            f"'{name}' is not a relationship method on model "
            f"[{self._model.__name__}]."
        )
