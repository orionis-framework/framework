import re
from typing import Any
from orionis.http.response import HTMLResponse
from orionis.view.contracts.engine import IViewEngine
from orionis.view.contracts.factory import IViewFactory
from orionis.view.exceptions import ViewRenderException

# Closure qualname noise (e.g. ``_global_csrf_field.<locals>.``) leaked by
# errors raised inside template globals; irrelevant for the developer.
_LOCALS_QUALNAME = re.compile(r"[\w.]*<locals>\.") # NOSONAR

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

    async def make(self, template: str, **context: Any) -> HTMLResponse:
        """
        Render a template and wrap the result in an :class:`HTMLResponse`.

        Parameters
        ----------
        template : str
            Template name using dot notation (e.g. ``'users.index'``) or a
            relative path (e.g. ``'users/index.html'``).
        **context : Any
            Keyword arguments forwarded as template variables.

        Returns
        -------
        HTMLResponse
            An HTTP response whose body is the rendered HTML content.

        Raises
        ------
        ViewTemplateNotFoundException
            When the view file cannot be located.
        ViewRenderException
            When rendering fails for any reason.
        """
        try:
            response_html: str = await self._engine.render(template, context)
            return HTMLResponse(
                content=response_html,
                headers={
                    "X-Orionis-Render": "SSR",
                },
            )
        except Exception as e:
            detail: str = _LOCALS_QUALNAME.sub("", str(e))
            exc_msg: str = f"Failed to render view '{template}': {detail}"
            raise ViewRenderException(exc_msg) from e
