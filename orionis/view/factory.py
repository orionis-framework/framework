# ruff: noqa: ANN401, TC001
# Retain arbitrary template context and the engine's injectable runtime type.
"""Prepare named templates for deferred rendering into HTML responses."""

from typing import Any
from orionis.view.contracts.engine import IViewEngine
from orionis.view.contracts.factory import IViewFactory
from orionis.view.pending import PendingView


class ViewFactory(IViewFactory):
    """
    Prepare named templates for deferred rendering into HTML responses.

    Create one :class:`orionis.view.pending.PendingView` per rendering operation.
    Call :meth:`make` synchronously to retain the context and queue response
    mutations. Await the returned value to render through the injected
    :class:`orionis.view.contracts.engine.IViewEngine` and obtain an
    :class:`orionis.http.HTMLResponse`.
    """

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
            No return value.
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

        Notes
        -----
        Template lookup and rendering errors are raised when the returned value
        is awaited, rather than when this method prepares it.
        """
        return PendingView(self._engine, template, context)
