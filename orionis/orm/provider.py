from __future__ import annotations
from orionis.container.providers.service_provider import ServiceProvider
from orionis.orm.contracts.query_builder import IQueryBuilder
from orionis.orm.query_builder import QueryBuilder
from orionis.support.facades.db import DB

class QueryBuilderProvider(ServiceProvider):

    def register(self) -> None:
        """
        Register the query builder as a singleton in the container.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.app.singleton(IQueryBuilder, QueryBuilder)

    async def boot(self) -> None:
        """
        Pin the query builder facade to the container.

        Returns
        -------
        None
            This method does not return a value.
        """
        await DB.pin()
