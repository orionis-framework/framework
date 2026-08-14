from __future__ import annotations
from typing import TYPE_CHECKING, Any
from orionis.orm.contracts.belongs_to_many_relation import IBelongsToManyRelation
from orionis.orm.metaclass import snake_case
from orionis.orm.query.raw_builder import RawQueryBuilder
from orionis.orm.relations.relation import Relation
from orionis.support.types.collection import Collection

if TYPE_CHECKING:
    from collections.abc import Iterable
    from orionis.orm.model import Model

class BelongsToManyRelation[TRelated: "Model"](
    Relation[TRelated],
    IBelongsToManyRelation,
):
    """
    Many-to-many relationship backed by an intermediate pivot table.

    Mirrors Eloquent's ``BelongsToMany``, with one deliberate difference:
    instead of compiling a single ``JOIN`` against the pivot table (which
    would require the SQL compiler to alias projected columns to avoid
    name collisions between both tables -- a feature it does not have
    yet), this relationship resolves in two steps:

    1. Query the pivot table for the related keys linked to the parent
       key(s) involved (:class:`RawQueryBuilder`, since the pivot table
       has no model).
    2. Query the related model table with ``whereIn(related_key, ids)``,
       reusing the regular, fully hydrated
       :class:`~orionis.orm.query.builder.ModelQueryBuilder` machinery.

    Composite pivot keys are out of scope: like the rest of the ORM,
    every key involved is a single column.
    """

    __slots__ = (
        "_foreign_pivot_key",
        "_parent_key",
        "_parent_keys",
        "_pivot_wheres",
        "_prepared",
        "_related_key",
        "_related_map",
        "_related_pivot_key",
        "_table",
    )

    def __init__(  # noqa: PLR0913
        self,
        parent: Model,
        related: type[TRelated],
        table: str | None,
        foreign_pivot_key: str | None,
        related_pivot_key: str | None,
        parent_key: str | None,
        related_key: str | None,
    ) -> None:
        """
        Bind the relationship.

        Parameters
        ----------
        parent : Model
            Model instance the relationship is accessed from.
        related : type of Model
            Model class the relationship targets.
        table : str or None
            Pivot table name; defaults to both model names in
            snake_case, singular, joined by ``"_"`` in alphabetical
            order (for instance ``role_user``).
        foreign_pivot_key : str or None
            Pivot column referencing the parent; defaults to
            ``snake_case(ParentClass) + "_id"``.
        related_pivot_key : str or None
            Pivot column referencing the related row; defaults to
            ``snake_case(RelatedClass) + "_id"``.
        parent_key : str or None
            Column on the parent matched against ``foreign_pivot_key``;
            defaults to the parent's primary key.
        related_key : str or None
            Column on the related table matched against
            ``related_pivot_key``; defaults to the related model's
            primary key.

        Returns
        -------
        None
            This method does not return a value.
        """
        parent_cls = type(parent)
        self._table = table or self._defaultPivotTable(parent_cls, related)
        self._foreign_pivot_key = (
            foreign_pivot_key or f"{snake_case(parent_cls.__name__)}_id"
        )
        self._related_pivot_key = (
            related_pivot_key or f"{snake_case(related.__name__)}_id"
        )
        self._parent_key = parent_key or parent_cls.__meta__.primary_key
        self._related_key = related_key or related.__meta__.primary_key
        self._parent_keys: tuple[Any, ...] = ()
        self._pivot_wheres: list[tuple[str, tuple[Any, ...]]] = []
        self._related_map: dict[Any, list[Any]] = {}
        self._prepared = False
        super().__init__(parent, related)

    @staticmethod
    def _defaultPivotTable(parent_cls: type[Model], related: type[Model]) -> str:
        """
        Derive the conventional pivot table name for two model classes.

        Parameters
        ----------
        parent_cls : type of Model
            Parent model class.
        related : type of Model
            Related model class.

        Returns
        -------
        str
            Both class names in snake_case, alphabetically joined by
            ``"_"``.
        """
        names = sorted((snake_case(parent_cls.__name__), snake_case(related.__name__)))
        return "_".join(names)

    # ── Relation template methods ────────────────────────────────────────────

    def addConstraints(self) -> None:
        """
        Capture the parent key used to resolve the pivot rows.

        The pivot query itself is deferred to :meth:`get`/other
        terminals, since resolving it requires an awaited query the
        constructor cannot perform.

        Returns
        -------
        None
            This method does not return a value.
        """
        value = getattr(self._parent, self._parent_key)
        self._parent_keys = (value,) if value is not None else ()

    def addEagerConstraints(self, models: list[Model]) -> None:
        """
        Capture every parent key involved in an eager-loaded batch.

        Parameters
        ----------
        models : list of Model
            Parent instances being eager loaded together.

        Returns
        -------
        None
            This method does not return a value.
        """
        keys = {
            value
            for model in models
            if (value := getattr(model, self._parent_key)) is not None
        }
        self._parent_keys = tuple(keys)

    def _pivotQuery(self) -> RawQueryBuilder:
        """
        Build a model-less query targeting the pivot table.

        Returns
        -------
        RawQueryBuilder
            Fresh builder bound to the pivot table and the connection
            the relationship runs on.
        """
        builder = RawQueryBuilder()
        if self._connection_name is not None:
            builder.connection(self._connection_name)
        return builder.table(self._table)

    async def getResults(self) -> Collection:
        """
        Retrieve every related row linked to the parent instance.

        Returns
        -------
        Collection
            Related models; empty when the parent has no key or no
            pivot row links it to anything.
        """
        return await self.get()

    def match(
        self,
        models: list[Model],
        results: Collection,
        name: str,
    ) -> None:
        """
        Attach the matching related rows to each parent instance.

        Parameters
        ----------
        models : list of Model
            Parent instances being eager loaded together.
        results : Collection
            Related rows produced by :meth:`getEager`.
        name : str
            Relationship name the results are stored under.

        Returns
        -------
        None
            This method does not return a value.
        """
        by_related_key = {getattr(row, self._related_key): row for row in results}
        for model in models:
            parent_value = getattr(model, self._parent_key)
            related_keys = self._related_map.get(parent_value, [])
            items = [
                by_related_key[key] for key in related_keys if key in by_related_key
            ]
            model.setRelation(name, Collection(items))

    # ── Pivot resolution ──────────────────────────────────────────────────

    async def _prepare(self) -> bool:
        """
        Resolve the pivot rows once and constrain the query to their ids.

        Idempotent: repeated terminal calls on the same relationship
        instance reuse the first resolution instead of re-querying the
        pivot table.

        Returns
        -------
        bool
            ``True`` when at least one related id was found.
        """
        if not self._prepared:
            self._related_map = await self._resolvePivotMap()
            self._prepared = True
        related_ids = sorted(
            {related_id for ids in self._related_map.values() for related_id in ids},
            key=str,
        )
        if not related_ids:
            return False
        self.whereIn(self._related_key, related_ids)
        return True

    async def _resolvePivotMap(self) -> dict[Any, list[Any]]:
        """
        Query the pivot table for the rows linking the captured parents.

        Returns
        -------
        dict
            Related ids grouped by the parent key that links to them.
        """
        if not self._parent_keys:
            return {}
        builder = self._pivotQuery()
        builder.whereIn(self._foreign_pivot_key, self._parent_keys)
        for column, args in self._pivot_wheres:
            builder.where(column, *args)
        rows = await builder.get()

        mapping: dict[Any, list[Any]] = {}
        for row in rows:
            parent_id = row[self._foreign_pivot_key]
            mapping.setdefault(parent_id, []).append(row[self._related_pivot_key])
        return mapping

    # ── Terminals resolving the pivot table before the related query ───────

    async def get(self) -> Collection:
        """
        Execute the query and hydrate every linked related row.

        Returns
        -------
        Collection
            Collection of hydrated related model instances.
        """
        if not await self._prepare():
            return Collection([])
        return await super().get()

    async def first(self) -> TRelated | None:
        """
        Execute the query and hydrate only the first linked related row.

        Returns
        -------
        Model or None
            First linked related model, or ``None`` without matches.
        """
        if not await self._prepare():
            return None
        return await super().first()

    async def count(self) -> int:
        """
        Count the related rows linked to the parent instance.

        Returns
        -------
        int
            Number of linked related rows.
        """
        if not await self._prepare():
            return 0
        return await super().count()

    async def exists(self) -> bool:
        """
        Report whether at least one related row is linked.

        Returns
        -------
        bool
            ``True`` when a linked related row exists.
        """
        if not await self._prepare():
            return False
        return await super().exists()

    # ── Pivot filtering ──────────────────────────────────────────────────────

    def wherePivot(
        self,
        column: str,
        *args: Any,  # noqa: ANN401
    ) -> BelongsToManyRelation[TRelated]:
        """
        Filter the pivot rows considered by this relationship query.

        Parameters
        ----------
        column : str
            Pivot table column name.
        *args : Any
            Either the bound value, or an operator followed by a value.

        Returns
        -------
        BelongsToManyRelation
            The same relationship, enabling fluent chaining.
        """
        self._pivot_wheres.append((column, args))
        return self

    # ── Pivot mutation ───────────────────────────────────────────────────────

    async def attach(
        self,
        ids: Any,  # noqa: ANN401
        attributes: dict[str, Any] | None = None,
    ) -> int:
        """
        Link the parent to the given related records via the pivot table.

        Parameters
        ----------
        ids : Any
            A related id, model instance, iterable of either, or a
            mapping of id (or model) to per-row pivot attributes.
        attributes : dict or None, optional
            Extra pivot column values applied to every inserted row when
            ``ids`` is not already a mapping.

        Returns
        -------
        int
            Number of pivot rows inserted.
        """
        parent_value = getattr(self._parent, self._parent_key)
        rows: list[dict[str, Any]] = []
        if isinstance(ids, dict):
            for key, extra in ids.items():
                rows.append({
                    self._foreign_pivot_key: parent_value,
                    self._related_pivot_key: self._extractId(key),
                    **extra,
                })
        else:
            rows.extend(
                {
                    self._foreign_pivot_key: parent_value,
                    self._related_pivot_key: related_id,
                    **(attributes or {}),
                }
                for related_id in self._normalizeIds(ids)
            )
        if not rows:
            return 0
        builder = self._pivotQuery()
        result = await builder.insert(rows)
        return result.row_count

    async def detach(self, ids: Any = None) -> int:  # noqa: ANN401
        """
        Unlink the parent from the given related records.

        Parameters
        ----------
        ids : Any, optional
            A related id, model instance, or iterable of either;
            ``None`` detaches every related record currently linked.

        Returns
        -------
        int
            Number of pivot rows deleted.
        """
        parent_value = getattr(self._parent, self._parent_key)
        builder = self._pivotQuery()
        builder.where(self._foreign_pivot_key, parent_value)
        if ids is not None:
            id_list = self._normalizeIds(ids)
            if not id_list:
                return 0
            builder.whereIn(self._related_pivot_key, id_list)
        return await builder.delete()

    async def sync(self, ids: Iterable[Any]) -> dict[str, list[Any]]:
        """
        Attach exactly the given records, detaching every other one.

        Parameters
        ----------
        ids : Iterable
            Related ids or model instances that must remain attached.

        Returns
        -------
        dict of str to list
            ``"attached"`` and ``"detached"`` related id lists.
        """
        target = set(self._normalizeIds(ids))
        current = set(await self._currentRelatedIds())
        to_attach = target - current
        to_detach = current - target
        if to_detach:
            await self.detach(list(to_detach))
        if to_attach:
            await self.attach(list(to_attach))
        return {
            "attached": sorted(to_attach, key=str),
            "detached": sorted(to_detach, key=str),
        }

    async def toggle(self, ids: Iterable[Any]) -> dict[str, list[Any]]:
        """
        Attach ids not currently linked, detach ids that already are.

        Parameters
        ----------
        ids : Iterable
            Related ids or model instances to toggle.

        Returns
        -------
        dict of str to list
            ``"attached"`` and ``"detached"`` related id lists.
        """
        id_list = self._normalizeIds(ids)
        current = set(await self._currentRelatedIds())
        to_attach = [related_id for related_id in id_list if related_id not in current]
        to_detach = [related_id for related_id in id_list if related_id in current]
        if to_detach:
            await self.detach(to_detach)
        if to_attach:
            await self.attach(to_attach)
        return {"attached": to_attach, "detached": to_detach}

    async def _currentRelatedIds(self) -> list[Any]:
        """
        Query the pivot table for the related ids currently linked.

        Returns
        -------
        list
            Related ids currently linked to the parent instance.
        """
        parent_value = getattr(self._parent, self._parent_key)
        builder = self._pivotQuery()
        builder.where(self._foreign_pivot_key, parent_value)
        builder.select(self._related_pivot_key)
        rows = await builder.get()
        return [row[self._related_pivot_key] for row in rows]

    def _normalizeIds(self, ids: Any) -> list[Any]:  # noqa: ANN401
        """
        Normalize a scalar, model, or iterable of either into id values.

        Parameters
        ----------
        ids : Any
            A related id, model instance, or iterable of either.

        Returns
        -------
        list
            Related id values.
        """
        if isinstance(ids, (list, tuple, set, frozenset, Collection)):
            return [self._extractId(item) for item in ids]
        return [self._extractId(ids)]

    def _extractId(self, item: Any) -> Any:  # noqa: ANN401
        """
        Extract the related key value from a scalar or model instance.

        Parameters
        ----------
        item : Any
            Related id, or a model instance to read the related key from.

        Returns
        -------
        Any
            Related id value.
        """
        # Imported locally: importing the Model class at module level
        # would cycle back through relations/mixin.py, which this module
        # is imported by.
        from orionis.orm.model import Model  # noqa: PLC0415

        if isinstance(item, Model):
            return getattr(item, self._related_key)
        return item
