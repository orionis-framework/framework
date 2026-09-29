from __future__ import annotations
import re
from copy import copy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from orionis.orm.attributes import get_cast_handler
from orionis.orm.exceptions import OrmConfigurationException
from orionis.orm.schema.column import ColumnDefinition
from orionis.orm.schema.table import TableDefinition

if TYPE_CHECKING:
    from collections.abc import Callable

# Pattern splitting CamelCase words for snake_case conversion.
_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")

# Suffixes that pluralize with "es".
_ES_SUFFIXES: tuple[str, ...] = ("s", "x", "z", "ch", "sh")

# English vowels used by the pluralization heuristic.
_VOWELS: frozenset[str] = frozenset("aeiou")

# Wildcard marking every attribute as guarded.
_GUARD_ALL: str = "*"

# Prefixes and suffix identifying the accessor/mutator naming convention.
_ACCESSOR_PREFIX: str = "get"
_MUTATOR_PREFIX: str = "set"
_ACCESSOR_SUFFIX: str = "Attribute"

# Prefix identifying a local query scope declared on a model.
_SCOPE_PREFIX: str = "scope"

# Lifecycle events a model can dispatch.
MODEL_EVENTS: tuple[str, ...] = (
    "retrieved",
    "saving",
    "creating",
    "created",
    "updating",
    "updated",
    "saved",
    "deleting",
    "deleted",
    "restoring",
    "restored",
)

# Builder entry points forwarded from the model class via the metaclass.
_FORWARDED_BUILDER_METHODS: frozenset[str] = frozenset({
    "addSelect",
    "avg",
    "count",
    "crossJoin",
    "distinct",
    "doesntExist",
    "exists",
    "forPage",
    "fullJoin",
    "get",
    "groupBy",
    "having",
    "havingRaw",
    "join",
    "joinSub",
    "latest",
    "leftJoin",
    "leftJoinSub",
    "limit",
    "load",
    "lockForUpdate",
    "max",
    "min",
    "offset",
    "oldest",
    "orHaving",
    "orWhere",
    "orWhereColumn",
    "orWhereExists",
    "orWhereIn",
    "orWhereNotExists",
    "orWhereNotIn",
    "orWhereNotNull",
    "orWhereNull",
    "orWhereRaw",
    "orderBy",
    "paginate",
    "pluck",
    "rightJoin",
    "rightJoinSub",
    "scope",
    "select",
    "selectRaw",
    "selectSub",
    "sharedLock",
    "skip",
    "sum",
    "take",
    "union",
    "unionAll",
    "value",
    "where",
    "whereBetween",
    "whereColumn",
    "whereContains",
    "whereEndsWith",
    "whereExists",
    "whereILike",
    "whereIn",
    "whereLike",
    "whereNotBetween",
    "whereNotExists",
    "whereNotILike",
    "whereNotIn",
    "whereNotLike",
    "whereNotNull",
    "whereNull",
    "whereRaw",
    "whereRegexpMatch",
    "whereStartsWith",
    "withRelations",
    "withTrashed",
    "withoutGlobalScope",
    "withoutGlobalScopes",
    "withoutTrashed",
    "onlyTrashed",
})

def snake_case(name: str) -> str:
    """
    Convert a CamelCase class name into snake_case.

    Leading underscores are ignored so private class names still map
    to clean table names.

    Parameters
    ----------
    name : str
        Class name to convert.

    Returns
    -------
    str
        snake_case version of the name.
    """
    return _CAMEL_BOUNDARY.sub("_", name.lstrip("_")).lower()

def pluralize(word: str) -> str:
    """
    Pluralize an English word using conventional heuristics.

    Parameters
    ----------
    word : str
        Singular word to pluralize.

    Returns
    -------
    str
        Pluralized word.
    """
    # Consonant + y becomes "ies" (category -> categories).
    if word.endswith("y") and len(word) > 1 and word[-2] not in _VOWELS:
        return word[:-1] + "ies"
    # Sibilant endings take "es" (box -> boxes).
    if word.endswith(_ES_SUFFIXES):
        return word + "es"
    return word + "s"

@dataclass(slots=True, eq=False)
class ModelMetadata:
    """
    Precomputed metadata describing a model class.

    Built once by the metaclass so hot paths (hydration, persistence)
    never perform reflection at runtime.

    Attributes
    ----------
    table_name : str
        Logical table name of the model.
    table : TableDefinition
        Table definition consumed by the SQL compiler.
    columns : dict of str to ColumnDefinition
        Column definitions keyed by attribute name.
    primary_key : str
        Name of the primary key column.
    casts : dict of str to str
        Declared cast names keyed by attribute name.
    cast_lookup : dict of str to Callable
        Precompiled cast handlers keyed by attribute name.
    fillable : frozenset of str
        Attributes allowed for mass assignment.
    guarded : frozenset of str
        Attributes blocked from mass assignment.
    hidden : frozenset of str
        Attributes omitted from serialization.
    timestamps : bool
        Whether the model maintains creation/update timestamps.
    incrementing : bool
        Whether the primary key is auto-incrementing.
    connection : str or None
        Named connection used by the model, or ``None`` for default.
    created_column : str or None
        Creation timestamp column, when present.
    updated_column : str or None
        Update timestamp column, when present.
    deleted_column : str or None
        Soft delete timestamp column, when the model soft deletes.
    uses_unique_ids : bool
        Whether the primary key is a client-generated unique identifier.
    accessors : dict of str to str
        Accessor method names keyed by the attribute they expose.
    mutators : dict of str to str
        Mutator method names keyed by the attribute they transform.
    appends : frozenset of str
        Accessor-backed attributes added to the serialized output.
    scopes : dict of str to str
        Local scope method names keyed by their fluent call name.
    global_scopes : dict of str to Callable
        Constraints applied to every query, keyed by scope name.
    events : dict of str to tuple
        Immutable (registration identity, listener) pairs keyed by event name.
    """

    table_name: str
    table: TableDefinition
    columns: dict[str, ColumnDefinition] = field(default_factory=dict)
    primary_key: str = "id"
    casts: dict[str, str] = field(default_factory=dict)
    cast_lookup: dict[str, Callable[[Any], Any]] = field(default_factory=dict)
    fillable: frozenset[str] = frozenset()
    guarded: frozenset[str] = frozenset()
    hidden: frozenset[str] = frozenset()
    timestamps: bool = True
    incrementing: bool = True
    connection: str | None = None
    created_column: str | None = None
    updated_column: str | None = None
    deleted_column: str | None = None
    uses_unique_ids: bool = False
    accessors: dict[str, str] = field(default_factory=dict)
    mutators: dict[str, str] = field(default_factory=dict)
    appends: frozenset[str] = frozenset()
    scopes: dict[str, str] = field(default_factory=dict)
    global_scopes: dict[str, Callable[[Any], None]] = field(default_factory=dict)
    events: dict[str, tuple[tuple[object, Callable[..., Any]], ...]] = field(
        default_factory=dict,
    )

    def isFillable(self, key: str) -> bool:
        """
        Report whether an attribute accepts mass assignment.

        Parameters
        ----------
        key : str
            Attribute name to check.

        Returns
        -------
        bool
            ``True`` when the attribute can be mass assigned.
        """
        # An explicit whitelist takes precedence over the guard list.
        if self.fillable:
            return key in self.fillable
        if self.guarded:
            return _GUARD_ALL not in self.guarded and key not in self.guarded
        return True

    def applyCasts(self, attributes: dict[str, Any]) -> dict[str, Any]:
        """
        Apply the declared casts to a raw attribute mapping in place.

        Parameters
        ----------
        attributes : dict
            Raw attribute values, typically a database row.

        Returns
        -------
        dict
            The same mapping with cast values applied.
        """
        for key, handler in self.cast_lookup.items():
            value = attributes.get(key)
            if value is not None:
                attributes[key] = handler(value)
        return attributes

class ModelMeta(type):
    """
    Metaclass discovering model columns and building their metadata.

    At class creation time the metaclass collects column definitions
    (including inherited ones), removes them from the class namespace so
    instance attribute access reaches the attribute store, derives the
    table name and primary key, and precompiles cast handlers.
    """

    def __new__( # NOSONAR
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,  # noqa: ANN401
    ) -> type:
        """
        Create the model class and attach its metadata.

        Parameters
        ----------
        name : str
            Name of the class being created.
        bases : tuple of type
            Base classes of the class being created.
        namespace : dict
            Class namespace as declared in the class body.
        **kwargs : Any
            Additional keyword arguments forwarded to ``type``.

        Returns
        -------
        type
            The created model class with ``__meta__`` attached.
        """
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        # Abstract classes (including the base model) defer their columns
        # to concrete descendants instead of building metadata.
        if not bases or namespace.get("__abstract__", False):
            cls.__pending_columns__ = mcs._collectPending(cls, namespace)
            cls.__meta__ = None
            return cls

        table = mcs._resolveTable(cls, name, namespace)
        columns = table.columns
        casts = mcs._collectCasts(cls)
        accessors, mutators, scopes = mcs._collectBehaviours(cls)
        events = mcs._inheritEvents(cls)

        # Timestamp columns are tracked only when actually declared.
        created = str(getattr(cls, "CREATED_AT", "created_at"))
        updated = str(getattr(cls, "UPDATED_AT", "updated_at"))
        deleted = str(getattr(cls, "DELETED_AT", "deleted_at"))
        timestamps = bool(getattr(cls, "timestamps", True))
        soft_deletes = bool(getattr(cls, "soft_deletes", False))
        deleted_column = deleted if soft_deletes and deleted in columns else None

        # A soft delete column must accept NULL to mark a live row.
        if deleted_column is not None and not columns[deleted_column].is_nullable:
            if getattr(cls, "table_definition", None) is not None:
                error_msg = "The shared soft delete column must be nullable."
                raise OrmConfigurationException(error_msg)
            columns[deleted_column] = copy(columns[deleted_column]).nullable()

        cls.__meta__ = ModelMetadata(
            table_name=table.name,
            table=table,
            columns=columns,
            primary_key=table.primary_key,
            casts=casts,
            cast_lookup={
                key: get_cast_handler(cast) for key, cast in casts.items()
            },
            fillable=frozenset(getattr(cls, "fillable", ()) or ()),
            guarded=frozenset(getattr(cls, "guarded", ()) or ()),
            hidden=frozenset(getattr(cls, "hidden", ()) or ()),
            timestamps=timestamps,
            incrementing=bool(getattr(cls, "incrementing", True)),
            connection=getattr(cls, "connection", None),
            created_column=created if timestamps and created in columns else None,
            updated_column=updated if timestamps and updated in columns else None,
            deleted_column=deleted_column,
            uses_unique_ids=bool(getattr(cls, "uuids", False)),
            accessors=accessors,
            mutators=mutators,
            appends=frozenset(getattr(cls, "appends", ()) or ()),
            scopes=scopes,
            global_scopes=mcs._inheritGlobalScopes(cls),
            events=events,
        )
        return cls

    def __getattr__(cls, name: str) -> Any:  # noqa: ANN401
        """
        Forward chainable builder entry points from the model class.

        Enables the Eloquent-style static API, e.g.
        ``User.where(...)`` starts a builder transparently.

        Parameters
        ----------
        name : str
            Attribute name requested on the model class.

        Returns
        -------
        Any
            Bound builder method for whitelisted entry points, or a
            bound local scope declared by the model.

        Raises
        ------
        AttributeError
            If the attribute is neither a forwarded builder method nor a
            local scope.
        """
        meta = cls.__dict__.get("__meta__")
        if meta is not None and (
            name in _FORWARDED_BUILDER_METHODS or name in meta.scopes
        ):
            return getattr(cls.query(), name)
        error_msg = (
            f"type object '{cls.__name__}' has no attribute '{name}'"
        )
        raise AttributeError(error_msg)

    # ── Discovery helpers ───────────────────────────────────────────────────

    @staticmethod
    def _resolveTable(
        owner: type,
        name: str,
        namespace: dict[str, Any],
    ) -> TableDefinition:
        """
        Resolve the shared table definition or inline model columns.

        Parameters
        ----------
        owner : type
            Model class being created.
        name : str
            Name of the model class.
        namespace : dict of str to Any
            Attributes declared in the model class body.

        Returns
        -------
        TableDefinition
            Resolved table definition for the model.

        Raises
        ------
        OrmConfigurationException
            If the shared definition is invalid, conflicts with model
            settings, or is combined with inline column declarations.
        """
        definition = getattr(owner, "table_definition", None)
        if definition is None:
            columns = ModelMeta._collectColumns(owner, namespace)
            return TableDefinition(
                name=ModelMeta._resolveTableName(owner, name, namespace),
                columns=columns,
                primary_key=ModelMeta._resolvePrimaryKey(owner, namespace, columns),
            )
        if not isinstance(definition, TableDefinition):
            error_msg = "Model.table_definition must be a TableDefinition."
            raise OrmConfigurationException(error_msg)
        if any(isinstance(value, ColumnDefinition) for value in namespace.values()):
            error_msg = "Declare columns in table_definition or on the model."
            raise OrmConfigurationException(error_msg)
        for key, expected in (
            ("table", definition.name), ("primary_key", definition.primary_key),
        ):
            configured = getattr(owner, key, None)
            if configured is not None and configured != expected:
                error_msg = f"Model.{key} conflicts with table_definition."
                raise OrmConfigurationException(error_msg)
        return definition

    @staticmethod
    def _collectPending(
        owner: type,
        namespace: dict[str, Any],
    ) -> dict[str, ColumnDefinition]:
        """
        Collect and detach column declarations from an abstract class.

        Parameters
        ----------
        owner : type
            Abstract class being created.
        namespace : dict
            Class namespace as declared in the class body.

        Returns
        -------
        dict of str to ColumnDefinition
            Columns deferred to concrete descendants.
        """
        pending: dict[str, ColumnDefinition] = {}

        # Inherit deferred columns from abstract ancestors.
        for base in reversed(owner.__mro__[1:]):
            inherited = base.__dict__.get("__pending_columns__")
            if inherited:
                pending.update(inherited)

        # Register own columns and detach them from the class body.
        for key, value in namespace.items():
            if isinstance(value, ColumnDefinition):
                value.name = key
                pending[key] = value
                delattr(owner, key)

        return pending

    @staticmethod
    def _collectColumns(
        owner: type,
        namespace: dict[str, Any],
    ) -> dict[str, ColumnDefinition]:
        """
        Collect column definitions from bases and the class namespace.

        Own declarations are removed from the class so instance access
        is served by the model attribute store.

        Parameters
        ----------
        owner : type
            Class being created.
        namespace : dict
            Class namespace as declared in the class body.

        Returns
        -------
        dict of str to ColumnDefinition
            Column definitions keyed by attribute name.
        """
        columns: dict[str, ColumnDefinition] = {}

        # Inherit columns from parent models in resolution order.
        for base in reversed(owner.__mro__[1:]):
            base_meta = base.__dict__.get("__meta__")
            if base_meta is not None:
                columns.update(base_meta.columns)
                continue
            deferred = base.__dict__.get("__pending_columns__")
            if deferred:
                columns.update(deferred)

        # Register own columns and detach them from the class body.
        for key, value in namespace.items():
            if isinstance(value, ColumnDefinition):
                value.name = key
                columns[key] = value
                delattr(owner, key)

        return columns

    @staticmethod
    def _resolveTableName(
        owner: type,
        name: str,
        namespace: dict[str, Any],
    ) -> str:
        """
        Resolve the table name from the declaration or the class name.

        Parameters
        ----------
        owner : type
            Class being created.
        name : str
            Name of the class being created.
        namespace : dict
            Class namespace as declared in the class body.

        Returns
        -------
        str
            Logical table name.
        """
        declared = namespace.get("table")
        if isinstance(declared, str) and declared.strip():
            return declared.strip()

        # Inherit an explicitly declared table from a parent model.
        inherited = getattr(owner, "table", None)
        if isinstance(inherited, str) and inherited.strip():
            return inherited.strip()

        return pluralize(snake_case(name))

    @staticmethod
    def _resolvePrimaryKey(
        owner: type,
        namespace: dict[str, Any],
        columns: dict[str, ColumnDefinition],
    ) -> str:
        """
        Resolve the primary key from declarations or column flags.

        Parameters
        ----------
        owner : type
            Class being created.
        namespace : dict
            Class namespace as declared in the class body.
        columns : dict of str to ColumnDefinition
            Collected column definitions.

        Returns
        -------
        str
            Primary key column name.
        """
        declared = namespace.get("primary_key") or getattr(
            owner, "primary_key", None,
        )
        if isinstance(declared, str) and declared.strip():
            return declared.strip()

        # Use the first column flagged as primary, defaulting to "id".
        for key, column in columns.items():
            if column.is_primary:
                return key
        return "id"

    @staticmethod
    def _collectCasts(owner: type) -> dict[str, str]:
        """
        Merge cast declarations across the model hierarchy.

        Parameters
        ----------
        owner : type
            Class being created.

        Returns
        -------
        dict of str to str
            Cast names keyed by attribute name.
        """
        casts: dict[str, str] = {}
        for base in reversed(owner.__mro__):
            declared = base.__dict__.get("casts")
            if isinstance(declared, dict):
                casts.update(declared)
        return casts

    @staticmethod
    def _behaviourEntry(name: str) -> tuple[str, str] | None:
        """
        Classify a method name as an accessor, mutator, or local scope.

        Parameters
        ----------
        name : str
            Method name declared on the model.

        Returns
        -------
        tuple of (str, str) or None
            The behaviour kind (``"accessor"``, ``"mutator"``, or
            ``"scope"``) and the key it registers under, or ``None``
            when the name follows no convention.
        """
        if name.endswith(_ACCESSOR_SUFFIX):
            for prefix, kind in (
                (_ACCESSOR_PREFIX, "accessor"),
                (_MUTATOR_PREFIX, "mutator"),
            ):
                if name.startswith(prefix):
                    middle = name[len(prefix) : -len(_ACCESSOR_SUFFIX)]
                    # ``getAttribute``/``setAttribute`` have no middle part.
                    if middle:
                        return kind, snake_case(middle)
        if name.startswith(_SCOPE_PREFIX) and len(name) > len(_SCOPE_PREFIX):
            suffix = name[len(_SCOPE_PREFIX) :]
            if suffix[0].isupper():
                return "scope", suffix[0].lower() + suffix[1:]
        return None

    @staticmethod
    def _collectBehaviours(
        owner: type,
    ) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        """
        Discover accessors, mutators, and local scopes of a model.

        Parameters
        ----------
        owner : type
            Class being created.

        Returns
        -------
        tuple of dict
            Accessors, mutators, and local scopes, each mapping their
            public key to the declaring method name.
        """
        registries: dict[str, dict[str, str]] = {
            "accessor": {},
            "mutator": {},
            "scope": {},
        }
        for base in reversed(owner.__mro__):
            for name, value in vars(base).items():
                # Scopes are declared as classmethods/staticmethods, whose
                # raw descriptors are not always callable themselves.
                if not callable(value) and not isinstance(
                    value, (classmethod, staticmethod),
                ):
                    continue
                entry = ModelMeta._behaviourEntry(name)
                if entry is not None:
                    kind, key = entry
                    registries[kind][key] = name
        return registries["accessor"], registries["mutator"], registries["scope"]

    @staticmethod
    def _inheritGlobalScopes(owner: type) -> dict[str, Callable[[Any], None]]:
        """
        Copy the global scopes declared by ancestor models.

        Parameters
        ----------
        owner : type
            Class being created.

        Returns
        -------
        dict of str to Callable
            Global scopes the new class starts with.
        """
        scopes: dict[str, Callable[[Any], None]] = {}
        for base in reversed(owner.__mro__[1:]):
            base_meta = base.__dict__.get("__meta__")
            if base_meta is not None:
                scopes.update(base_meta.global_scopes)
        return scopes

    @staticmethod
    def _inheritEvents(
        owner: type,
    ) -> dict[str, tuple[tuple[object, Callable[..., Any]], ...]]:
        """
        Copy the lifecycle listeners declared by ancestor models.

        Parameters
        ----------
        owner : type
            Class being created.

        Returns
        -------
        dict of str to tuple
            Listener snapshots with their registration identities.
        """
        events: dict[str, list[tuple[object, Callable[..., Any]]]] = {}
        covered: set[type] = set()
        seen: set[object] = set()
        for base in owner.__mro__[1:]:
            if base in covered:
                continue
            base_meta = base.__dict__.get("__meta__")
            if base_meta is None:
                continue
            covered.update(base.__mro__)
            for event, registrations in base_meta.events.items():
                for registration in registrations:
                    token = registration[0]
                    if token not in seen:
                        seen.add(token)
                        events.setdefault(event, []).append(registration)
        return {event: tuple(entries) for event, entries in events.items()}
