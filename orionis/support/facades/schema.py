from orionis.container.facades.facade import Facade
from orionis.database.contracts.schema import ISchema

class Schema(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[ISchema]:
        """
        Return the facade accessor string for the unit test contract.

        Returns
        -------
        type
            The facade contract type.
        """
        return ISchema
