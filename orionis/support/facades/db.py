from orionis.container.facades.facade import Facade
from orionis.orm.contracts.query_builder import IQueryBuilder

class DB(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the container accessor for the database gateway.

        Returns
        -------
        type
            :class:`IQueryBuilder`.
        """
        return IQueryBuilder
