from typing import Any
from orionis.view.contracts.engine import IViewEngine
from orionis.view.contracts.factory import IViewFactory
from orionis.view.pending import PendingView

class ViewFactory(IViewFactory):
    """
    Render named templates and return :class:`HTMLResponse` objects.

    :class:`ViewFactory` is the primary entry-point for controllers and
    other HTTP-layer code that needs to produce HTML responses from
    templates.  It delegates all rendering work to the bound
    :class:`IViewEngine` and wraps the output in a framework-native
    :class:`HTMLResponse`.
    """

    # ruff: noqa: ANN401, TC001

    __slots__ = ("_engine",)

    def __init__(self, engine: IViewEngine) -> None:
        """
        Initialise the factory with a rendering engine.

        Parameters
        ----------
        engine : IViewEngine
            The view engine used to render templates.

        Returns
        -------
        None
        """
        self._engine: IViewEngine = engine

    def make(self, template: str, **context: Any) -> PendingView:
        """
        Prepare a template render as an awaitable, chainable response.

        Parameters
        ----------
        template : str
            Template name using dot notation (e.g. ``'users.index'``) or a
            relative path (e.g. ``'users/index.html'``).
        **context : Any
            Keyword arguments forwarded as template variables.

        Returns
        -------
        PendingView
            Awaitable proxy that renders the template on ``await`` and
            accepts chained response mutators such as ``withFlash()``,
            ``withCookie()`` or ``withoutCookie()``.

        Raises
        ------
        ViewTemplateNotFoundException
            When the view file cannot be located.
        ViewRenderException
            When rendering fails for any reason.
        """
        return PendingView(self._engine, template, context)
