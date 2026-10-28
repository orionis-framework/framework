from orionis.container.facades.facade import Facade

class Debug(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> str:
        """Return the container alias for the dumper contract.

        Returns
        -------
        str
            Alias used to resolve the registered dumper service.
        """
        return "x-orionis-IDumper"
