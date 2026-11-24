from orionis.container.facades.facade import Facade
from orionis.database.contracts.transaction import ITransaction
from orionis.orm.contracts.query_builder import IQueryBuilder
from orionis.orm.contracts.raw_builder import IRawQueryBuilder

class DB(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[IQueryBuilder]: ...

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> IQueryBuilder: ...

    @classmethod
    def connection(cls, name: str | None = None) -> IQueryBuilder: ...

    @classmethod
    def table(
        cls,
        name: str,
        *,
        alias: str | None = None,
        connection: str | None = None,
    ) -> IRawQueryBuilder: ...

    @classmethod
    def getDefaultName(cls) -> str: ...

    @classmethod
    def setDefaultName(cls, name: str) -> None: ...

    @classmethod
    async def select(
        cls,
        sql: str,
        bindings: dict[str, object] | None = None,
        name: str | None = None,
    ) -> list[dict[str, object]]: ...

    @classmethod
    async def execute(
        cls,
        sql: str,
        bindings: dict[str, object] | None = None,
        name: str | None = None,
    ) -> int: ...

    @classmethod
    async def statement(
        cls,
        sql: str,
        bindings: dict[str, object] | None = None,
        name: str | None = None,
    ) -> bool: ...

    @classmethod
    async def beginTransaction(cls, name: str | None = None) -> None: ...

    @classmethod
    async def commit(cls, name: str | None = None) -> None: ...

    @classmethod
    async def rollback(cls, name: str | None = None) -> None: ...

    @classmethod
    def transaction(cls, name: str | None = None) -> ITransaction: ...
