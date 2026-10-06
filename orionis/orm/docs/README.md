# orionis.orm

> API reference derived from the current implementation.

## Table of contents

- Requirements
- Functional overview
- Module structure
- API reference
- Usage examples
- Design characteristics
- Performance and concurrency
- Compatibility notes
- Verification and limitations

## Requirements

Python 3.14 or newer, as declared by pyproject.toml.

## Functional overview

The orionis.orm initializer exports 57 public symbols. This reference uses __all__, export routes, and current source files as evidence.

## Module structure

| Path | Responsibility |
| --- | --- |
| ../__init__.py | Defines package exports. |
| orionis.orm/ | Implementations and subpackages for those exports. |

## API reference

| Symbol | Verified import | Source | Declaration | Observed behavior |
| --- | --- | --- | --- | --- |
| BelongsToManyRelation | from orionis.orm import BelongsToManyRelation | [relations/__init__.py](../relations/__init__.py) | exported constant or alias | Exported public constant or alias. |
| BelongsToRelation | from orionis.orm import BelongsToRelation | [relations/__init__.py](../relations/__init__.py) | exported constant or alias | Exported public constant or alias. |
| BigInteger | from orionis.orm import BigInteger | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Boolean | from orionis.orm import Boolean | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Collection | from orionis.orm import Collection | [collections/collection.py](../collections/collection.py) | exported constant or alias | Exported public constant or alias. |
| ColumnType | from orionis.orm import ColumnType | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| ConnectionResolver | from orionis.orm import ConnectionResolver | [resolver.py](../resolver.py) | ConnectionResolver | Static bridge between the ORM and the database connection manager. The database service provider installs the manager here during boot; models and query builders resolve their connections through this class without ever touching the container or the SQL engine. |
| ConnectionResolver.setManager | from orionis.orm import ConnectionResolver | [resolver.py](../resolver.py) | def setManager(cls, manager: IConnectionManager) -> None | Install the connection manager used by every model. Parameters ---------- manager : IConnectionManager Manager resolving named database connections. Returns ------- None This method does not return a value. |
| ConnectionResolver.manager | from orionis.orm import ConnectionResolver | [resolver.py](../resolver.py) | def manager(cls) -> IConnectionManager | Return the installed connection manager. Returns ------- IConnectionManager Manager resolving named database connections. Raises ------ OrmConfigurationException If no manager has been installed yet. |
| ConnectionResolver.connection | from orionis.orm import ConnectionResolver | [resolver.py](../resolver.py) | def connection(cls, name: str / None) -> IConnection | Resolve a database connection by name. Parameters ---------- name : str or None, optional Connection name, or ``None`` for the default connection. Returns ------- IConnection Resolved connection. Raises ------ OrmConfigurationException If no manager has been installed yet. ConnectionNotFoundException If the connection is not declared in the configuration. |
| ConnectionResolver.clear | from orionis.orm import ConnectionResolver | [resolver.py](../resolver.py) | def clear(cls) -> None | Remove the installed manager, mainly for test isolation. Returns ------- None This method does not return a value. |
| Date | from orionis.orm import Date | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| DateTime | from orionis.orm import DateTime | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Double | from orionis.orm import Double | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Enum | from orionis.orm import Enum | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Float | from orionis.orm import Float | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| HasManyRelation | from orionis.orm import HasManyRelation | [relations/__init__.py](../relations/__init__.py) | exported constant or alias | Exported public constant or alias. |
| HasOneRelation | from orionis.orm import HasOneRelation | [relations/__init__.py](../relations/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Integer | from orionis.orm import Integer | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Interval | from orionis.orm import Interval | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| InvalidQueryException | from orionis.orm import InvalidQueryException | [exceptions/__init__.py](../exceptions/__init__.py) | InvalidQueryException | Raised when a query builder call receives invalid arguments. |
| LargeBinary | from orionis.orm import LargeBinary | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| MassAssignmentException | from orionis.orm import MassAssignmentException | [exceptions/__init__.py](../exceptions/__init__.py) | MassAssignmentException | Raised when a mass assignment violates the fillable/guarded rules. |
| MatchType | from orionis.orm import MatchType | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Model | from orionis.orm import Model | [model.py](../model.py) | Model | Base class of the Orionis active-record models. Concrete models declare their columns with the fluent schema types and interact with the database exclusively through the Orionis query builder; the underlying SQL engine never surfaces. Class-level entry points such as ``where`` or ``orderBy`` start a builder implicitly. |
| Model.query | from orionis.orm import Model | [model.py](../model.py) | def query(cls) -> ModelQueryBuilder[Any] | Start a new query builder bound to this model. Returns ------- ModelQueryBuilder Fresh builder targeting the model table. |
| Model.getConnection | from orionis.orm import Model | [model.py](../model.py) | def getConnection(cls) -> IConnection | Resolve the connection configured for this model. Returns ------- IConnection Connection used for model queries and persistence. Raises ------ OrmConfigurationException If no connection manager has been installed. ConnectionNotFoundException If the configured connection is not declared. |
| Model.addGlobalScope | from orionis.orm import Model | [model.py](../model.py) | def addGlobalScope(cls, name: str, scope: Callable[[ModelQueryBuilder[Any]], None]) -> type[Model] | Register a constraint applied to every query of this model. Parameters ---------- name : str Name the scope is registered under, used to disable it later with ``withoutGlobalScope``. scope : Callable Callable receiving the builder and constraining it in place. Returns ------- type The model class, enabling fluent chaining. |
| Model.removeGlobalScope | from orionis.orm import Model | [model.py](../model.py) | def removeGlobalScope(cls, name: str) -> type[Model] | Unregister a previously added global scope. Parameters ---------- name : str Name the scope was registered under. Returns ------- type The model class, enabling fluent chaining. |
| Model.all | from orionis.orm import Model | [model.py](../model.py) | async def all(cls) -> Collection | Retrieve every row of the model table. Returns ------- Collection Collection of hydrated model instances. |
| Model.find | from orionis.orm import Model | [model.py](../model.py) | async def find(cls, key: Any) -> Model / None | Retrieve a model by its primary key. Parameters ---------- key : Any Primary key value to look up. Returns ------- Model or None Matching model, or ``None`` when absent. |
| Model.findOrFail | from orionis.orm import Model | [model.py](../model.py) | async def findOrFail(cls, key: Any) -> Model | Retrieve a model by primary key or raise when absent. Parameters ---------- key : Any Primary key value to look up. Returns ------- Model Matching model. Raises ------ ModelNotFoundException If no record matches the key. |
| Model.first | from orionis.orm import Model | [model.py](../model.py) | async def first(cls) -> Model / None | Retrieve the first row of the model table. Returns ------- Model or None First model, or ``None`` when the table is empty. |
| Model.firstOrFail | from orionis.orm import Model | [model.py](../model.py) | async def firstOrFail(cls) -> Model | Retrieve the first row or raise when the table is empty. Returns ------- Model First model. Raises ------ ModelNotFoundException If the table has no rows. |
| Model.create | from orionis.orm import Model | [model.py](../model.py) | async def create(cls, attributes: dict[str, Any]) -> Model | Create, persist, and return a new model. Parameters ---------- attributes : dict Attributes to mass assign honoring the fillable rules. Returns ------- Model Persisted model instance. Raises ------ MassAssignmentException If an attribute violates the mass assignment rules. QueryException If the insert statement fails. |
| Model.destroy | from orionis.orm import Model | [model.py](../model.py) | async def destroy(cls, *keys) -> int | Delete the models matching the given primary keys. Parameters ---------- *keys : Any Primary key values to delete. Returns ------- int Number of deleted rows. |
| Model.save | from orionis.orm import Model | [model.py](../model.py) | async def save(self) -> bool | Persist the model, inserting or updating as appropriate. New models are inserted, receiving their generated primary key; existing models write only their dirty attributes. Timestamps are maintained automatically when enabled, and the ``saving``, ``creating``/``updating``, ``created``/``updated`` and ``saved`` events are dispatched around the write. Returns ------- bool ``True`` when the operation succeeds or nothing changed, ``False`` when a listener vetoed the write. Raises ------ QueryException If the statement fails to execute. |
| Model.update | from orionis.orm import Model | [model.py](../model.py) | async def update(self, attributes: dict[str, Any]) -> bool | Mass assign the given attributes and persist the model. Parameters ---------- attributes : dict Attributes to assign honoring the fillable rules. Returns ------- bool ``True`` when the operation succeeds or nothing changed. Raises ------ MassAssignmentException If an attribute violates the mass assignment rules. QueryException If the statement fails to execute. |
| Model.delete | from orionis.orm import Model | [model.py](../model.py) | async def delete(self) -> bool | Delete the model row, honoring soft deletes when enabled. Models declaring ``soft_deletes`` stamp their delete column instead of removing the row; every other model is deleted permanently. Returns ------- bool ``True`` when a row was deleted or stamped, ``False`` for unsaved models or when a listener vetoed the operation. Raises ------ QueryException If the statement fails to execute. |
| Model.freshTimestamp | from orionis.orm import Model | [model.py](../model.py) | def freshTimestamp(cls) -> datetime | Produce the current timestamp for persistence operations. Timezone-aware timestamps are produced when the update column is a timezone-aware type, naive UTC otherwise. Returns ------- datetime Current UTC timestamp. |
| Model.newUniqueId | from orionis.orm import Model | [model.py](../model.py) | def newUniqueId(cls) -> Any | Produce a client-generated primary key value. Overridable by models needing a different identifier scheme, such as ULIDs or prefixed keys. Returns ------- Any Fresh unique identifier. |
| ModelCollection | from orionis.orm import ModelCollection | [collections/collection.py](../collections/collection.py) | exported constant or alias | Exported public constant or alias. |
| ModelNotFoundException | from orionis.orm import ModelNotFoundException | [exceptions/__init__.py](../exceptions/__init__.py) | ModelNotFoundException | Raised when a model lookup that must succeed finds no records. |
| ModelQueryBuilder | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | ModelQueryBuilder | Fluent query builder bound to a model class. It adds model awareness on top of :class:`QueryBuilderBase`: rows are hydrated into model instances, written values go through the declared casts, timestamps are maintained, and relationships can be eager loaded. The query language itself is entirely inherited, so a model query and a ``DB.table(...)`` query compile identically. |
| ModelQueryBuilder.withRelations | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | def withRelations(self, *names) -> Self | Eager load the given relationships alongside the query. Each relationship is loaded once in declaration order; :meth:`load` is an alias. Parameters ---------- *names : str Relationship method names declared on the model. Returns ------- ModelQueryBuilder The same builder, enabling fluent chaining. |
| ModelQueryBuilder.load | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | def load(self, *names) -> Self | Eager load the given relationships; alias of :meth:`withRelations`. Parameters ---------- *names : str Relationship method names declared on the model. Returns ------- ModelQueryBuilder The same builder, enabling fluent chaining. |
| ModelQueryBuilder.withoutGlobalScope | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | def withoutGlobalScope(self, name: str) -> Self | Disable one global scope for this query. Parameters ---------- name : str Name the global scope was registered under. Returns ------- ModelQueryBuilder The same builder, enabling fluent chaining. |
| ModelQueryBuilder.withoutGlobalScopes | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | def withoutGlobalScopes(self, *names) -> Self | Disable several global scopes, or every one of them. Parameters ---------- *names : str Scope names to disable; empty disables all of them. Returns ------- ModelQueryBuilder The same builder, enabling fluent chaining. |
| ModelQueryBuilder.scope | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | def scope(self, name: str, *args, **kwargs) -> Self | Apply a local scope by name. Useful when the scope name collides with a builder method; the attribute form (``query.active()``) is the common one. Parameters ---------- name : str Scope name, without the ``scope`` prefix. *args : Any Positional arguments forwarded to the scope. **kwargs : Any Keyword arguments forwarded to the scope. Returns ------- ModelQueryBuilder The same builder, enabling fluent chaining. Raises ------ ScopeNotFoundException If the model declares no such scope. |
| ModelQueryBuilder.withTrashed | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | def withTrashed(self) -> Self | Include soft deleted rows in the query results. Returns ------- ModelQueryBuilder The same builder, enabling fluent chaining. |
| ModelQueryBuilder.onlyTrashed | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | def onlyTrashed(self) -> Self | Restrict the query to soft deleted rows. Returns ------- ModelQueryBuilder The same builder, enabling fluent chaining. |
| ModelQueryBuilder.withoutTrashed | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | def withoutTrashed(self) -> Self | Exclude soft deleted rows; the default behavior. Returns ------- ModelQueryBuilder The same builder, enabling fluent chaining. |
| ModelQueryBuilder.restore | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | async def restore(self) -> int | Restore every soft deleted row matched by the query. Returns ------- int Number of restored rows. |
| ModelQueryBuilder.forceDelete | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | async def forceDelete(self) -> int | Delete the matched rows permanently, ignoring soft deletes. Returns ------- int Number of affected rows. |
| ModelQueryBuilder.delete | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | async def delete(self) -> int | Delete the matched rows, honoring soft deletes when enabled. Returns ------- int Number of affected rows. |
| ModelQueryBuilder.get | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | async def get(self) -> Collection | Execute the query and hydrate every matching row. Returns ------- Collection Collection of hydrated model instances. Raises ------ QueryException If the statement fails to compile or execute. RelationNotFoundException If an eager-loaded relationship name does not resolve to one. |
| ModelQueryBuilder.first | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | async def first(self) -> TModel / None | Execute the query and hydrate only the first matching row. Returns ------- Model or None First matching model, or ``None`` without matches. Raises ------ QueryException If the statement fails to compile or execute. RelationNotFoundException If an eager-loaded relationship name does not resolve to one. |
| ModelQueryBuilder.firstOrFail | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | async def firstOrFail(self) -> TModel | Return the first matching row or raise when none exists. Returns ------- Model First matching model. Raises ------ ModelNotFoundException If the query yields no rows. |
| ModelQueryBuilder.find | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | async def find(self, key: Any) -> TModel / None | Retrieve a model by its primary key. Parameters ---------- key : Any Primary key value to look up. Returns ------- Model or None Matching model, or ``None`` when absent. |
| ModelQueryBuilder.findOrFail | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | async def findOrFail(self, key: Any) -> TModel | Retrieve a model by primary key or raise when absent. Parameters ---------- key : Any Primary key value to look up. Returns ------- Model Matching model. Raises ------ ModelNotFoundException If no record matches the key. |
| ModelQueryBuilder.value | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | async def value(self, column: str) -> Any | Return a single column value of the first matching row. Parameters ---------- column : str Column whose value is returned. Returns ------- Any Column value, or ``None`` without matches. |
| ModelQueryBuilder.pluck | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | async def pluck(self, column: str) -> Collection | Return one column of every matching row. Parameters ---------- column : str Column whose values are collected. Returns ------- Collection Collection of column values. |
| ModelQueryBuilder.paginate | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | async def paginate(self, page: int, per_page: int) -> Paginator | Execute the query returning a length-aware page of results. Parameters ---------- page : int, optional Page number starting at 1. Defaults to the first page. per_page : int, optional Number of items per page. Defaults to 15. Returns ------- Paginator Page of hydrated models with pagination metadata. Raises ------ InvalidQueryException If the page or page size are not positive integers. |
| ModelQueryBuilder.clone | from orionis.orm import ModelQueryBuilder | [query/builder.py](../query/builder.py) | def clone(self) -> Self | Return an independent copy of this builder. Returns ------- ModelQueryBuilder Detached copy carrying its own plan and eager-load list. |
| Numeric | from orionis.orm import Numeric | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| NumericCommon | from orionis.orm import NumericCommon | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| OrmConfigurationException | from orionis.orm import OrmConfigurationException | [exceptions/__init__.py](../exceptions/__init__.py) | OrmConfigurationException | Raised when the ORM is used before its wiring is complete. |
| OrmException | from orionis.orm import OrmException | [exceptions/__init__.py](../exceptions/__init__.py) | OrmException | Base exception for all ORM-related errors. |
| Paginator | from orionis.orm import Paginator | [collections/paginator.py](../collections/paginator.py) | Paginator | Length-aware page of query results. Wraps a :class:`Collection` of items together with the pagination metadata required to render page controls: total row count, current page, page size, and derived navigation flags. |
| Paginator.items | from orionis.orm import Paginator | [collections/paginator.py](../collections/paginator.py) | def items(self) -> Collection | Return the items for the current page. Returns ------- Collection Items of the current page. |
| Paginator.total | from orionis.orm import Paginator | [collections/paginator.py](../collections/paginator.py) | def total(self) -> int | Return the total number of rows across all pages. Returns ------- int Total row count. |
| Paginator.page | from orionis.orm import Paginator | [collections/paginator.py](../collections/paginator.py) | def page(self) -> int | Return the current page number. Returns ------- int Current page, starting at 1. |
| Paginator.perPage | from orionis.orm import Paginator | [collections/paginator.py](../collections/paginator.py) | def perPage(self) -> int | Return the configured page size. Returns ------- int Number of items per page. |
| Paginator.lastPage | from orionis.orm import Paginator | [collections/paginator.py](../collections/paginator.py) | def lastPage(self) -> int | Return the number of the last available page. Returns ------- int Last page number, never lower than 1. |
| Paginator.hasNext | from orionis.orm import Paginator | [collections/paginator.py](../collections/paginator.py) | def hasNext(self) -> bool | Report whether a page exists after the current one. Returns ------- bool ``True`` when the current page is not the last. |
| Paginator.hasPrevious | from orionis.orm import Paginator | [collections/paginator.py](../collections/paginator.py) | def hasPrevious(self) -> bool | Report whether a page exists before the current one. Returns ------- bool ``True`` when the current page is not the first. |
| Paginator.toDict | from orionis.orm import Paginator | [collections/paginator.py](../collections/paginator.py) | def toDict(self) -> dict[str, Any] | Serialize the page and its metadata into a dictionary. Returns ------- dict Dictionary with items and pagination metadata. |
| Paginator.toJson | from orionis.orm import Paginator | [collections/paginator.py](../collections/paginator.py) | def toJson(self, **kwargs) -> str | Serialize the page and its metadata into a JSON string. Parameters ---------- **kwargs : Any Additional keyword arguments forwarded to ``json.dumps``. Returns ------- str JSON representation of the page. |
| PickleType | from orionis.orm import PickleType | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Relation | from orionis.orm import Relation | [relations/__init__.py](../relations/__init__.py) | exported constant or alias | Exported public constant or alias. |
| RelationNotFoundException | from orionis.orm import RelationNotFoundException | [exceptions/__init__.py](../exceptions/__init__.py) | RelationNotFoundException | Raised when a relationship name cannot be resolved on a model. |
| SchemaType | from orionis.orm import SchemaType | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| SmallInteger | from orionis.orm import SmallInteger | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictArray | from orionis.orm import StrictArray | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictBigInt | from orionis.orm import StrictBigInt | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictBinary | from orionis.orm import StrictBinary | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictBlob | from orionis.orm import StrictBlob | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictChar | from orionis.orm import StrictChar | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictClob | from orionis.orm import StrictClob | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictDecimal | from orionis.orm import StrictDecimal | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictDoublePrecision | from orionis.orm import StrictDoublePrecision | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictInt | from orionis.orm import StrictInt | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictJson | from orionis.orm import StrictJson | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictNChar | from orionis.orm import StrictNChar | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictNVarChar | from orionis.orm import StrictNVarChar | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictReal | from orionis.orm import StrictReal | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictSmallInt | from orionis.orm import StrictSmallInt | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictTimestamp | from orionis.orm import StrictTimestamp | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictVarBinary | from orionis.orm import StrictVarBinary | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| StrictVarChar | from orionis.orm import StrictVarChar | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| String | from orionis.orm import String | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Text | from orionis.orm import Text | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Time | from orionis.orm import Time | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Unicode | from orionis.orm import Unicode | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| UnicodeText | from orionis.orm import UnicodeText | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |
| Uuid | from orionis.orm import Uuid | [schema/types/__init__.py](../schema/types/__init__.py) | exported constant or alias | Exported public constant or alias. |

## Usage examples

    from orionis.orm import BelongsToManyRelation

The import path matches the API table. Import status: executed successfully under Python 3.14.3.

## Design characteristics

The package uses an explicit public surface. Private names are excluded; declarations link to their concrete owner.

## Performance and concurrency

No uniform guarantee is declared at package level. Inspect each linked file for I/O, coroutines, caches, locks, and shared state.

## Compatibility notes

Declared minimum: Python 3.14. Validation used Python 3.14.3. Dependency bounds are in pyproject.toml.

## Verification and limitations

Python files were analysed and exports verified. Failures from dependencies, callbacks, I/O, or configuration may propagate and are not presented as exhaustive.
