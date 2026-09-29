from __future__ import annotations
from orionis.container.contracts.deferrable_provider import IDeferrableProvider

class DeferrableProvider(IDeferrableProvider):
    """
    Mark service providers that support deferred loading.

    This is a marker interface used to identify service providers that can
    defer their initialization until actually needed by the container.
    """

    @classmethod
    def provides(cls) -> list[type | str]:
        """
        Return the services provided by this provider.

        Returns
        -------
        list[type | str]
            A list of service types or string identifiers that this provider offers.

        Raises
        ------
        NotImplementedError
            When subclasses do not implement this method.
        """
        error_msg = "Subclasses must implement the provides method."
        raise NotImplementedError(error_msg)
