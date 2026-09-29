from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class IViewEngine(ABC):
    """
    Contract for view engine implementations.

    All rendering engines registered with the view system must implement
    this interface so that the rest of the framework remains decoupled from
    any concrete template technology.
    """

    __slots__ = ()

    @abstractmethod
    async def render(self, template: str, context: dict[str, Any]) -> str:
        """
        Render a template with the supplied context and return HTML.

        Parameters
        ----------
        template : str
            Template identifier.  Engines are free to interpret this string
            (e.g. dot notation ``'users.index'`` or a bare filename).
        context : dict[str, Any]
            Mapping of variable names to values made available inside the
            template during rendering.

        Returns
        -------
        str
            The rendered HTML string produced by the engine.

        Raises
        ------
        ViewTemplateNotFoundException
            When the requested template file cannot be located.
        ViewRenderException
            When the template engine fails to render the template.
        """
