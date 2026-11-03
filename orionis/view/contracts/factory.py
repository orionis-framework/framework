"""Contract for the view factory."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.view.pending import PendingView

class IViewFactory(ABC):
    """
    Contract for the view factory.

    Callers use this interface to render named templates and receive
    fully formed :class:`orionis.http.HTMLResponse` objects ready to return from
    HTTP controllers.
    """

    # ruff: noqa: ANN401

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def make(self, template: str, **context: Any) -> PendingView:
        """
        Prepare a template render as an awaitable, chainable response.

        Parameters
        ----------
        template : str
            Template name using dot notation (e.g. ``'users.index'``) or a
            direct path relative to a configured template directory.
        **context : typing.Any
            Keyword arguments are forwarded as template variables.

        Returns
        -------
        orionis.view.pending.PendingView
            Awaitable proxy that resolves to an :class:`orionis.http.HTMLResponse` and
            accepts chained response mutators such as ``withFlash()``.

        Raises
        ------
        orionis.view.exceptions.ViewTemplateNotFoundException
            When the requested template file cannot be located.
        orionis.view.exceptions.ViewRenderException
            When the template engine fails during rendering.
        """
