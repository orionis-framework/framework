# ruff: noqa: ANN401
# Column values, expressions and registered scope arguments are dynamic.
# pyright: reportGeneralTypeIssues=false
# ModelMeta binds these methods only to Model subclasses. A generic receiver
# preserves each subclass on the builder returned by its class-level calls.
from collections.abc import Callable, Iterable
from typing import Any
from orionis.orm.collections.paginator import Paginator
from orionis.orm.model import Model
from orionis.orm.query.builder import ModelQueryBuilder
from orionis.orm.query.join_clause import JoinClause
from orionis.orm.schema.table import TableDefinition
from orionis.support.types.collection import Collection

class _ModelQueryMeta(type):

    def toSql(cls, *, literal_binds: bool = False) -> str: ...

    def select[TModel: Model](
        cls: type[TModel],
        *columns: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def addSelect[TModel: Model](
        cls: type[TModel],
        *columns: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def selectRaw[TModel: Model](
        cls: type[TModel],
        sql: str,
        bindings: dict[str, Any] | None = None,
        alias: str | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def selectSub[TModel: Model](
        cls: type[TModel],
        query: Any,
        alias: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def distinct[TModel: Model](cls: type[TModel]) -> ModelQueryBuilder[TModel]: ...

    def where[TModel: Model](
        cls: type[TModel],
        column: Any,
        *args: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def orWhere[TModel: Model](
        cls: type[TModel],
        column: Any,
        *args: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereIn[TModel: Model](
        cls: type[TModel],
        column: str,
        values: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def orWhereIn[TModel: Model](
        cls: type[TModel],
        column: str,
        values: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereNotIn[TModel: Model](
        cls: type[TModel],
        column: str,
        values: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def orWhereNotIn[TModel: Model](
        cls: type[TModel],
        column: str,
        values: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereNull[TModel: Model](
        cls: type[TModel],
        column: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def orWhereNull[TModel: Model](
        cls: type[TModel],
        column: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereNotNull[TModel: Model](
        cls: type[TModel],
        column: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def orWhereNotNull[TModel: Model](
        cls: type[TModel],
        column: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereBetween[TModel: Model](
        cls: type[TModel],
        column: str,
        bounds: Iterable[Any],
    ) -> ModelQueryBuilder[TModel]: ...

    def whereNotBetween[TModel: Model](
        cls: type[TModel],
        column: str,
        bounds: Iterable[Any],
    ) -> ModelQueryBuilder[TModel]: ...

    def whereLike[TModel: Model](
        cls: type[TModel],
        column: str,
        pattern: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereNotLike[TModel: Model](
        cls: type[TModel],
        column: str,
        pattern: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereILike[TModel: Model](
        cls: type[TModel],
        column: str,
        pattern: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereNotILike[TModel: Model](
        cls: type[TModel],
        column: str,
        pattern: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereStartsWith[TModel: Model](
        cls: type[TModel],
        column: str,
        value: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereEndsWith[TModel: Model](
        cls: type[TModel],
        column: str,
        value: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereContains[TModel: Model](
        cls: type[TModel],
        column: str,
        value: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereRegexpMatch[TModel: Model](
        cls: type[TModel],
        column: str,
        pattern: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereColumn[TModel: Model](
        cls: type[TModel],
        first: str,
        operator: str,
        second: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def orWhereColumn[TModel: Model](
        cls: type[TModel],
        first: str,
        operator: str,
        second: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereRaw[TModel: Model](
        cls: type[TModel],
        sql: str,
        bindings: dict[str, Any] | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def orWhereRaw[TModel: Model](
        cls: type[TModel],
        sql: str,
        bindings: dict[str, Any] | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereExists[TModel: Model](
        cls: type[TModel],
        query: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def orWhereExists[TModel: Model](
        cls: type[TModel],
        query: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def whereNotExists[TModel: Model](
        cls: type[TModel],
        query: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def orWhereNotExists[TModel: Model](
        cls: type[TModel],
        query: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def join[TModel: Model](
        cls: type[TModel],
        table: str | TableDefinition,
        first: str | Callable[[JoinClause], object] | None = None,
        operator: str | None = None,
        second: str | None = None,
        *,
        alias: str | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def leftJoin[TModel: Model](
        cls: type[TModel],
        table: str | TableDefinition,
        first: str | Callable[[JoinClause], object] | None = None,
        operator: str | None = None,
        second: str | None = None,
        *,
        alias: str | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def rightJoin[TModel: Model](
        cls: type[TModel],
        table: str | TableDefinition,
        first: str | Callable[[JoinClause], object] | None = None,
        operator: str | None = None,
        second: str | None = None,
        *,
        alias: str | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def fullJoin[TModel: Model](
        cls: type[TModel],
        table: str | TableDefinition,
        first: str | Callable[[JoinClause], object] | None = None,
        operator: str | None = None,
        second: str | None = None,
        *,
        alias: str | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def crossJoin[TModel: Model](
        cls: type[TModel],
        table: str | TableDefinition,
        *,
        alias: str | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def joinSub[TModel: Model](
        cls: type[TModel],
        query: Any,
        alias: str,
        first: str | Callable[[JoinClause], object] | None = None,
        operator: str | None = None,
        second: str | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def leftJoinSub[TModel: Model](
        cls: type[TModel],
        query: Any,
        alias: str,
        first: str | Callable[[JoinClause], object] | None = None,
        operator: str | None = None,
        second: str | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def rightJoinSub[TModel: Model](
        cls: type[TModel],
        query: Any,
        alias: str,
        first: str | Callable[[JoinClause], object] | None = None,
        operator: str | None = None,
        second: str | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def orderBy[TModel: Model](
        cls: type[TModel],
        column: str,
        direction: str = "asc",
    ) -> ModelQueryBuilder[TModel]: ...

    def latest[TModel: Model](
        cls: type[TModel],
        column: str | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def oldest[TModel: Model](
        cls: type[TModel],
        column: str | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def groupBy[TModel: Model](
        cls: type[TModel],
        *columns: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def having[TModel: Model](
        cls: type[TModel],
        column: Any,
        *args: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def orHaving[TModel: Model](
        cls: type[TModel],
        column: Any,
        *args: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def havingRaw[TModel: Model](
        cls: type[TModel],
        sql: str,
        bindings: dict[str, Any] | None = None,
    ) -> ModelQueryBuilder[TModel]: ...

    def limit[TModel: Model](
        cls: type[TModel],
        value: int,
    ) -> ModelQueryBuilder[TModel]: ...

    def offset[TModel: Model](
        cls: type[TModel],
        value: int,
    ) -> ModelQueryBuilder[TModel]: ...

    def take[TModel: Model](
        cls: type[TModel],
        value: int,
    ) -> ModelQueryBuilder[TModel]: ...

    def skip[TModel: Model](
        cls: type[TModel],
        value: int,
    ) -> ModelQueryBuilder[TModel]: ...

    def forPage[TModel: Model](
        cls: type[TModel],
        page: int,
        per_page: int = 15,
    ) -> ModelQueryBuilder[TModel]: ...

    def lockForUpdate[TModel: Model](
        cls: type[TModel],
    ) -> ModelQueryBuilder[TModel]: ...

    def sharedLock[TModel: Model](cls: type[TModel]) -> ModelQueryBuilder[TModel]: ...

    def union[TModel: Model](
        cls: type[TModel],
        query: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def unionAll[TModel: Model](
        cls: type[TModel],
        query: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    async def count(cls, column: str = "*") -> int: ...

    async def exists(cls) -> bool: ...

    async def doesntExist(cls) -> bool: ...

    async def max(cls, column: str) -> Any: ...

    async def min(cls, column: str) -> Any: ...

    async def avg(cls, column: str) -> float | None: ...

    async def sum(cls, column: str) -> Any: ...

    def withRelations[TModel: Model](
        cls: type[TModel],
        *names: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def load[TModel: Model](
        cls: type[TModel],
        *names: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def withoutGlobalScope[TModel: Model](
        cls: type[TModel],
        name: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def withoutGlobalScopes[TModel: Model](
        cls: type[TModel],
        *names: str,
    ) -> ModelQueryBuilder[TModel]: ...

    def scope[TModel: Model](
        cls: type[TModel],
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> ModelQueryBuilder[TModel]: ...

    def withTrashed[TModel: Model](cls: type[TModel]) -> ModelQueryBuilder[TModel]: ...

    def onlyTrashed[TModel: Model](cls: type[TModel]) -> ModelQueryBuilder[TModel]: ...

    def withoutTrashed[TModel: Model](
        cls: type[TModel],
    ) -> ModelQueryBuilder[TModel]: ...

    async def get[TModel: Model](cls: type[TModel]) -> Collection[TModel]: ...

    async def value(cls, column: str) -> Any: ...

    async def pluck(cls, column: str) -> Collection[Any]: ...

    async def paginate[TModel: Model](
        cls: type[TModel],
        page: int = 1,
        per_page: int = 15,
    ) -> Paginator[TModel]: ...
