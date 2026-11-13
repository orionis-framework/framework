"""Resolve the db service through the application facade."""

from orionis.container.facades.facade import Facade
from orionis.orm.contracts.query_builder import IQueryBuilder


class DB(Facade):
    """Resolve the db service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the container accessor for the database gateway.

        Returns
        -------
        type
            :class:`orionis.orm.contracts.query_builder.IQueryBuilder`.
        """
        return IQueryBuilder
