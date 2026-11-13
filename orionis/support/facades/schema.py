"""Resolve the schema service through the application facade."""

from orionis.container.facades.facade import Facade
from orionis.database.contracts.schema import ISchema


class Schema(Facade):
    """Resolve the schema service through the application facade."""

    @classmethod
    def getFacadeAccessor(cls) -> type[ISchema]:
        """
        Return the contract used to resolve schema operations.

        Returns
        -------
        type
            The facade contract type.
        """
        return ISchema
