from typing import TYPE_CHECKING, Self
from orionis.database.contracts.connection import IConnection
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.contracts.schema import ISchema
from orionis.database.migrations.context import current_migration_connection
from orionis.database.schema.column import Column
from orionis.database.schema.comment import Comment
from orionis.database.schema.definition_bucket import DefinitionBucket
from orionis.database.schema.foreign import ForeignKey
from orionis.database.schema.index import Index
from orionis.database.schema.primary import PrimaryKey
from orionis.database.schema.table_creation import TableCreation
from orionis.database.schema.timestamp import Timestamps
from orionis.database.schema.unique import Unique
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.column import ColumnDefinition
from orionis.orm.metaclass import ModelMeta

if TYPE_CHECKING:
    from orionis.database.schema.definitions import SchemaDefinition
    from orionis.orm.model import Model

class Schema(ISchema):

    # ruff: noqa: TC001

    __slots__ = (
        "__conn_manager", "__connection_name", "__connection_selected",
    )

    def __init__(self, conn_manager: IConnectionManager) -> None:
        """
        Initialize the Schema instance.

        Parameters
        ----------
        conn_manager : IConnectionManager
            The connection manager for database operations.

        Returns
        -------
        None
        """
        # Initialize connection manager and state attributes
        self.__conn_manager: IConnectionManager = conn_manager
        self.__connection_name: str | None = None
        self.__connection_selected = False

    def connection(self, name: str | None = None) -> Self:
        """
        Set the connection name for schema operations.

        Parameters
        ----------
        name : str | None, optional
            The connection name to use, by default None.

        Returns
        -------
        Self
            The current Schema instance for method chaining.

        Raises
        ------
        ValueError
            If connection name has already been defined.
        """
        # Prevent overwriting an already set connection name
        if self.__connection_selected:
            error_msg = "Connection name has already been defined."
            raise ValueError(error_msg)
        self.__connection_name = name
        self.__connection_selected = True
        return self

    def create(self, name: str) -> TableCreation:
        """
        Start a fluent table declaration block.

        ``async with schema.create(name) as table:`` yields a
        :class:`~orionis.database.schema.blueprint.Blueprint` so columns
        can be declared fluently (``table.string("username")``,
        ``table.timestamps()``, ...); the table is created once the
        block exits without raising.

        Parameters
        ----------
        name : str
            The name of the table to create. If the table belongs to a
            non-default schema, use the ``schema.table`` format.

        Returns
        -------
        TableCreation
            Async context manager that collects definitions and creates
            the table after a successful block.
        """
        return TableCreation(self, name)

    async def createFromDefinition(self, definition: TableDefinition) -> bool:
        """
        Create a table from its reusable, versioned definition.

        Parameters
        ----------
        definition : TableDefinition
            Schema shared with a model through ``table_definition``.
            Historical migrations should import a versioned definition
            that remains unchanged when the model adopts a newer version.

        Returns
        -------
        bool
            Whether table creation completed successfully.
        """
        return await self.__resolveConnection().createTable(definition)

    async def createFromModel(self, model: type[Model]) -> bool:
        """
        Create the current schema declared by a concrete model.

        Use this operation for bootstrap and temporary databases. A historical
        migration should call ``createFromDefinition`` with a versioned table
        definition so later model changes do not alter migration replay.

        Parameters
        ----------
        model : type of Model
            Concrete model providing table and connection metadata. An explicit
            ``connection`` selection overrides the model's connection.

        Returns
        -------
        bool
            Whether table creation completed successfully.

        Raises
        ------
        TypeError
            If the argument is not a concrete model class.
        """
        metadata = (
            model.__dict__.get("__meta__")
            if isinstance(model, ModelMeta) else None
        )
        if metadata is None:
            error_msg = "Expected a concrete model class with table metadata."
            raise TypeError(error_msg)
        connection_name = (
            self.__connection_name if self.__connection_selected
            else metadata.connection
        )
        connection = (
            current_migration_connection()
            if not self.__connection_selected and connection_name is None
            else None
        )
        if connection is None:
            connection = self.__conn_manager.connection(connection_name)
        return await connection.createTable(metadata.table)

    async def drop(self, name: str) -> bool:
        """
        Drop an existing table.

        Parameters
        ----------
        name : str
            The name of the table to drop. If the table belongs to a
            non-default schema, use the ``schema.table`` format.

        Returns
        -------
        bool
            ``True`` when the table is dropped without errors.
        """
        connection: IConnection = self.__resolveConnection()
        schema, table = self.__parseTableName(name)
        return await connection.dropTable(name=table, schema=schema)

    async def _createTable(
        self,
        name: str,
        definitions: tuple[SchemaDefinition, ...],
    ) -> bool:
        """
        Compile and execute the ``CREATE TABLE`` for ``name``.

        Parameters
        ----------
        name : str
            The name of the table to create.
        definitions : tuple
            Schema definitions collected for the table.

        Returns
        -------
        bool
            ``True`` when the table is created without errors.
        """
        connection: IConnection = self.__resolveConnection()
        return await connection.createTable(self.__buildTable(name, definitions))

    def __resolveConnection(self) -> IConnection:
        """
        Resolve the connection bound to the configured connection name.

        Returns
        -------
        IConnection
            The connection to use for schema operations.
        """
        # Use the migration transaction for unqualified schema operations.
        if not self.__connection_selected:
            migration_connection = current_migration_connection()
            if migration_connection is not None:
                return migration_connection
        return self.__conn_manager.connection(self.__connection_name)

    def __buildTable(
        self,
        name: str,
        definitions: tuple[SchemaDefinition, ...],
    ) -> TableDefinition:
        """
        Build the table definition from a name and its definitions.

        Parameters
        ----------
        name : str
            The name of the table to build, possibly ``schema.table``.
        definitions : tuple
            Schema definitions collected for the table.

        Returns
        -------
        TableDefinition
            The complete table definition ready for compilation.
        """
        schema, table = self.__parseTableName(name)
        kwargs = self.__collectDefinitions(definitions)
        return TableDefinition(name=table, schema=schema, **kwargs)

    def __collectDefinitions(
        self,
        definitions: tuple[SchemaDefinition, ...],
    ) -> dict[str, object]:
        """
        Group heterogeneous schema definitions into constructor kwargs.

        Parameters
        ----------
        definitions : tuple
            Column, constraint, index, and comment definitions to sort.

        Returns
        -------
        dict[str, object]
            Keyword arguments accepted by ``TableDefinition``.
        """
        # Group columns and constraints by their declaration kinds.
        bucket = DefinitionBucket()
        for definition in definitions:
            self.__classifyDefinition(definition, bucket)

        # Apply primary keys declared via Column.primary() after the
        # loop, so duplicates against an explicit PrimaryKey() raise.
        if bucket.primary_columns:
            self.__setPrimaryKey(bucket.primary_columns, bucket.kwargs)

        bucket.kwargs["columns"] = bucket.columns
        # Omit empty collections so TableDefinition defaults apply.
        if bucket.unique_constraints:
            bucket.kwargs["unique_constraints"] = tuple(
                bucket.unique_constraints,
            )
        if bucket.foreign_keys:
            bucket.kwargs["foreign_keys"] = tuple(bucket.foreign_keys)
        if bucket.indexes:
            bucket.kwargs["indexes"] = tuple(bucket.indexes)
        return bucket.kwargs

    def __classifyDefinition(
        self,
        definition: (
            ColumnDefinition
            | Comment
            | ForeignKey
            | Index
            | PrimaryKey
            | Unique
        ),
        bucket: DefinitionBucket,
    ) -> None:
        """
        Route a single schema definition into the shared bucket.

        Parameters
        ----------
        definition : ColumnDefinition | Comment | ForeignKey | Index |
            PrimaryKey | Unique
            The schema definition to classify.
        bucket : DefinitionBucket
            Accumulator updated in place with the classified data.

        Returns
        -------
        None
            The ``bucket`` accumulator is mutated in place.
        """
        # Register columns and collect their primary key declarations.
        if isinstance(definition, ColumnDefinition):
            bucket.columns[definition.name] = definition
            # Column-level .primary() also defines the primary key.
            if definition.is_primary:
                bucket.primary_columns.append(definition.name)
            return

        if isinstance(definition, Comment):
            bucket.kwargs["comment"] = definition.text
        elif isinstance(definition, Unique):
            bucket.unique_constraints.append(definition.constraint)
        elif isinstance(definition, ForeignKey):
            bucket.foreign_keys.append(definition.foreign)
        elif isinstance(definition, Index):
            bucket.indexes.append(definition.constraint)
        elif isinstance(definition, PrimaryKey):
            self.__setPrimaryKey(list(definition.columns), bucket.kwargs)
        elif isinstance(definition, Timestamps):
            self.__addTimestampColumns(definition, bucket)
        else:
            error_msg = f"Unsupported schema definition: {type(definition).__name__}."
            raise TypeError(error_msg)

    def __addTimestampColumns(
        self,
        definition: Timestamps,
        bucket: DefinitionBucket,
    ) -> None:
        """
        Expand a ``Timestamps`` marker into its two nullable columns.

        Parameters
        ----------
        definition : Timestamps
            The timestamps marker carrying the ``timezone`` flag.
        bucket : DefinitionBucket
            Accumulator updated in place with the new columns.

        Returns
        -------
        None
            The ``bucket`` accumulator is mutated in place.
        """
        for column_name in ("created_at", "updated_at"):
            column = Column.dateTime(column_name, timezone=definition.timezone)
            column.nullable()
            bucket.columns[column_name] = column

    def __setPrimaryKey(
        self,
        column_names: list[str],
        kwargs: dict[str, object],
    ) -> None:
        """
        Assign the primary key columns, rejecting duplicate definitions.

        Parameters
        ----------
        column_names : list[str]
            Names of the columns composing the primary key.
        kwargs : dict[str, object]
            Accumulated ``TableDefinition`` keyword arguments, updated
            in place.

        Returns
        -------
        None
            The ``kwargs`` mapping is mutated in place.

        Raises
        ------
        ValueError
            If a primary key was already defined.
        """
        if "primary_key" in kwargs or "composite_primary_key" in kwargs:
            error_msg = "Primary key has already been defined."
            raise ValueError(error_msg)
        # A single column keeps the simple form; more than one composes
        # a composite primary key instead.
        if len(column_names) > 1:
            kwargs["composite_primary_key"] = tuple(column_names)
        else:
            kwargs["primary_key"] = column_names[0]

    def __parseTableName(self, name: str) -> tuple[str | None, str]:
        """
        Parse the table name to extract schema and table components.

        Parameters
        ----------
        name : str
            The full table name, which may include a schema prefix.

        Returns
        -------
        tuple[str | None, str]
            A tuple containing the schema name (or None if not specified)
            and the table name.
        """
        schema, separator, table = name.partition(".")
        if not schema or (separator and (not table or "." in table)):
            error_msg = "Expected a table name or a 'schema.table' identifier."
            raise ValueError(error_msg)
        return (schema, table) if separator else (None, schema)
