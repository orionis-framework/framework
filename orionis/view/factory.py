# ruff: noqa: ANN401, TC001
# Retain arbitrary template context and the engine's injectable runtime type.
"""Prepare named templates for deferred rendering into HTML responses."""

from collections.abc import Mapping
from typing import Any
from orionis.background.task import BackgroundTask
from orionis.http.enums.status import HTTPStatus
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

    def make(
        self,
        template: str,
        *,
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
        context: Mapping[str, Any] | None = None,
        **variables: Any,
    ) -> PendingView:
        """
        Prepare a template render as an awaitable, chainable response.

        Parameters
        ----------
        template : str
            Template name using dot notation (e.g. ``'users.index'``) or a
            relative path (e.g. ``'users/index.html'``).
        status_code : orionis.http.enums.HTTPStatus | int, optional
            HTTP status code for the rendered response.
        headers : collections.abc.Mapping[str, str] | None, optional
            Response headers. The SSR marker is added when not supplied.
        background : orionis.background.BackgroundTask | None, optional
            Task to run after the response is sent.
        context : collections.abc.Mapping[str, typing.Any] | None, optional
            Template variables, including names reserved for response options.
        **variables : typing.Any
            Additional template variables, overriding matching context entries.

        Returns
        -------
        orionis.view.pending.PendingView
            Awaitable proxy that renders the template on ``await`` and
            accepts chained response mutators such as ``withStatusCode()``,
            ``withHeaders()``, ``withBackground()`` or ``withErrors()``.

        Raises
        ------
        TypeError
            If *context* is neither a mapping nor ``None``.

        Notes
        -----
        Template lookup and rendering errors are raised when the returned value
        is awaited, rather than when this method prepares it.
        Response options are also validated on await; chained mutations are
        applied after the initial options, in call order.
        """
        if context is not None:
            if not isinstance(context, Mapping):
                error_msg = "context must be a mapping or None"
                raise TypeError(error_msg)
            variables = {**context, **variables}

        return PendingView(
            self._engine,
            template,
            variables,
            status_code=status_code,
            headers=headers,
            background=background,
        )
