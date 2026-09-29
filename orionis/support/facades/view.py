from __future__ import annotations
from orionis.container.facades.facade import Facade
from orionis.view.contracts.factory import IViewFactory

class View(Facade):
    """
    Facade for the view factory.

    Proxies all calls to the bound :class:`IViewFactory` singleton,
    enabling controllers to render templates without explicit dependency
    injection.

    Usage (facade pinned at boot)::

        return await View.make("users.index", users=users)
        return await View.make("auth.login")
    """

    @classmethod
    def getFacadeAccessor(cls) -> type:
        """
        Return the container accessor for the view factory.

        Returns
        -------
        type
            :class:`IViewFactory`.
        """
        return IViewFactory
