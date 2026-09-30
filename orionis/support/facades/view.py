from __future__ import annotations
from orionis.container.facades.facade import Facade
from orionis.view.contracts.factory import IViewFactory

class View(Facade):

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
