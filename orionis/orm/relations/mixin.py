from __future__ import annotations
from typing import TYPE_CHECKING, Any
from orionis.orm.relations.belongs_to import BelongsToRelation
from orionis.orm.relations.belongs_to_many import BelongsToManyRelation
from orionis.orm.relations.has_many import HasManyRelation
from orionis.orm.relations.has_one import HasOneRelation

if TYPE_CHECKING:
    from orionis.orm.model import Model

class RelationsMixin:
    """
    Relationship factories and loaded-relation storage for every model.

    Concrete models declare relationships as regular instance methods
    calling the factories below, mirroring Eloquent::

        class User(Model):
            def posts(self):
                return self.hasMany(Post)

            def profile(self):
                return self.hasOne(Profile)

    Instance methods (rather than class-body descriptors) are used
    deliberately: a descriptor such as ``posts = hasMany(Post)`` would be
    evaluated while the class body executes, which breaks the moment two
    related models reference each other from separate modules (or even
    from the same module when one is declared after the other) -- a
    forward-reference problem regular methods sidestep entirely, since
    their body only runs once every involved class already exists.

    The mixin also owns the ``_relations`` mapping every model instance
    carries, used to cache eager-loaded results
    (:meth:`~orionis.orm.query.builder.ModelQueryBuilder.withRelations`).
    """

    __slots__ = ()

    # ── Relationship factories ──────────────────────────────────────────────

    def hasOne[TRelated: "Model"](
        self,
        related: type[TRelated],
        foreign_key: str | None = None,
        local_key: str | None = None,
    ) -> HasOneRelation[TRelated]:
        """
        Define a one-to-one relationship owned by the related table.

        Parameters
        ----------
        related : type of Model
            Model class the relationship targets.
        foreign_key : str or None, optional
            Column on the related table referencing this model; defaults
            to ``snake_case(ThisClass) + "_id"``.
        local_key : str or None, optional
            Column on this model compared against the foreign key;
            defaults to this model's primary key.

        Returns
        -------
        HasOneRelation
            Relationship query builder bound to this instance.
        """
        return HasOneRelation(self, related, foreign_key, local_key)

    def hasMany[TRelated: "Model"](
        self,
        related: type[TRelated],
        foreign_key: str | None = None,
        local_key: str | None = None,
    ) -> HasManyRelation[TRelated]:
        """
        Define a one-to-many relationship owned by the related table.

        Parameters
        ----------
        related : type of Model
            Model class the relationship targets.
        foreign_key : str or None, optional
            Column on the related table referencing this model; defaults
            to ``snake_case(ThisClass) + "_id"``.
        local_key : str or None, optional
            Column on this model compared against the foreign key;
            defaults to this model's primary key.

        Returns
        -------
        HasManyRelation
            Relationship query builder bound to this instance.
        """
        return HasManyRelation(self, related, foreign_key, local_key)

    def belongsTo[TRelated: "Model"](
        self,
        related: type[TRelated],
        foreign_key: str | None = None,
        owner_key: str | None = None,
    ) -> BelongsToRelation[TRelated]:
        """
        Define the inverse of a ``hasOne``/``hasMany`` relationship.

        Parameters
        ----------
        related : type of Model
            Model class the relationship targets.
        foreign_key : str or None, optional
            Column on this model referencing the related row; defaults
            to ``snake_case(RelatedClass) + "_id"``.
        owner_key : str or None, optional
            Column on the related table identifying the owning row;
            defaults to the related model's primary key.

        Returns
        -------
        BelongsToRelation
            Relationship query builder bound to this instance.
        """
        return BelongsToRelation(self, related, foreign_key, owner_key)

    def belongsToMany[TRelated: "Model"](  # noqa: PLR0913
        self,
        related: type[TRelated],
        table: str | None = None,
        foreign_pivot_key: str | None = None,
        related_pivot_key: str | None = None,
        parent_key: str | None = None,
        related_key: str | None = None,
    ) -> BelongsToManyRelation[TRelated]:
        """
        Define a many-to-many relationship backed by a pivot table.

        Parameters
        ----------
        related : type of Model
            Model class the relationship targets.
        table : str or None, optional
            Pivot table name; defaults to both model names in
            snake_case, joined by ``"_"`` in alphabetical order.
        foreign_pivot_key : str or None, optional
            Pivot column referencing this model; defaults to
            ``snake_case(ThisClass) + "_id"``.
        related_pivot_key : str or None, optional
            Pivot column referencing the related row; defaults to
            ``snake_case(RelatedClass) + "_id"``.
        parent_key : str or None, optional
            Column on this model matched against ``foreign_pivot_key``;
            defaults to this model's primary key.
        related_key : str or None, optional
            Column on the related table matched against
            ``related_pivot_key``; defaults to the related model's
            primary key.

        Returns
        -------
        BelongsToManyRelation
            Relationship query builder bound to this instance.
        """
        return BelongsToManyRelation(
            self,
            related,
            table,
            foreign_pivot_key,
            related_pivot_key,
            parent_key,
            related_key,
        )

    # ── Loaded relation storage ──────────────────────────────────────────────

    def setRelation(self, name: str, value: Any) -> Model:  # noqa: ANN401
        """
        Store an already-resolved relationship result.

        Parameters
        ----------
        name : str
            Relationship name.
        value : Any
            Resolved relationship result (a model, ``None``, or a
            Collection, depending on the relationship kind).

        Returns
        -------
        Model
            The same instance, enabling fluent chaining.
        """
        self._relations[name] = value
        return self

    def getRelation(self, name: str, default: Any = None) -> Any:  # noqa: ANN401
        """
        Return an already-resolved relationship result.

        Parameters
        ----------
        name : str
            Relationship name.
        default : Any, optional
            Value returned when the relationship was never loaded.

        Returns
        -------
        Any
            Stored relationship result, or the default when unset.
        """
        return self._relations.get(name, default)

    def relationLoaded(self, name: str) -> bool:
        """
        Report whether a relationship result has already been resolved.

        Parameters
        ----------
        name : str
            Relationship name.

        Returns
        -------
        bool
            ``True`` when the relationship was already loaded, whether
            by eager loading or a prior :meth:`setRelation` call.
        """
        return name in self._relations
