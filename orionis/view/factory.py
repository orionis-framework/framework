"""Render named templates and return :class:`orionis.http.HTMLResponse` objects."""

from typing import Any
from orionis.view.contracts.engine import IViewEngine
from orionis.view.contracts.factory import IViewFactory
from orionis.view.pending import PendingView

class ViewFactory(IViewFactory):
    """
    Render named templates and return :class:`orionis.http.HTMLResponse` objects.

    :class:`orionis.view.factory.ViewFactory` is the primary entry-point for controllers
    and
    other HTTP-layer code that needs to produce HTML responses from
    templates.  It delegates all rendering work to the bound
    :class:`orionis.view.contracts.engine.IViewEngine` and wraps the output in a
    framework-native
    :class:`orionis.http.HTMLResponse`.
    """

    # ruff: noqa: ANN401, TC001

    __slots__ = ("_engine",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, engine: IViewEngine) -> None:
        """
        Initialise the factory with a rendering engine.

        Parameters
        ----------
        engine : orionis.view.contracts.engine.IViewEngine
            The view engine used to render templates.

        Returns
        -------
        None
            Initialise the factory with a rendering engine.
        """
        self._engine: IViewEngine = engine
        """The view engine used to render templates."""

    def make(self, template: str, **context: Any) -> PendingView:
        """
        Prepare a template render as an awaitable, chainable response.

        Parameters
        ----------
        template : str
            Template name using dot notation (e.g. ``'users.index'``) or a
            relative path (e.g. ``'users/index.html'``).
        **context : typing.Any
            Keyword arguments forwarded as template variables.

        Returns
        -------
        orionis.view.pending.PendingView
            Awaitable proxy that renders the template on ``await`` and
            accepts chained response mutators such as ``withInput()``,
            ``withErrors()``, ``withFlash()``, ``withCookie()`` or
            ``withoutCookie()``.

        Raises
        ------
        orionis.view.exceptions.ViewTemplateNotFoundException
            When the view file cannot be located.
        orionis.view.exceptions.ViewRenderException
            When rendering fails for any reason.
        """
        return PendingView(self._engine, template, context)
