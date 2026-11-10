"""Provide awaitable, chainable results of template rendering."""

from __future__ import annotations
import re
from typing import TYPE_CHECKING, Any, Self
from orionis.http.responses import HTMLResponse
from orionis.session.flash import _FlashData, apply_flash
from orionis.support.facades.session import Session
from orionis.view.exceptions import ViewRenderException, ViewTemplateNotFoundException

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from orionis.session.contracts.session import ISession
    from orionis.view.contracts.engine import IViewEngine

# Closure qualname noise (e.g. ``_global_csrf_field.<locals>.``) leaked by
# errors raised inside template globals; irrelevant for the developer.
_LOCALS_QUALNAME = re.compile(r"[\w.]*<locals>\.")  # NOSONAR
"""
Closure qualname noise (e.g. ``_global_csrf_field.<locals>.``) leaked by errors
raised inside template globals; irrelevant for the developer.
"""

class PendingView(_FlashData):
    """
    Represent an awaitable, chainable template rendering result.

    Created by :meth:`orionis.view.contracts.factory.IViewFactory.make`.

    Rendering is deferred until the object is awaited, so response
    mutators such as ``withInput()``, ``withErrors()``, ``withFlash()``
    or ``withCookie()`` can be chained directly on the ``make()`` call::

        return await View.make("auth.login").withErrors(errors)

    Every attribute that exists on :class:`orionis.http.HTMLResponse` is accepted and
    replayed on the real response once the template has been rendered.
    """

    # ruff: noqa: ANN401, BLE001

    __slots__ = ("_context", "_engine", "_flash", "_mutations", "_template")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self: Self,
        engine: IViewEngine,
        template: str,
        context: dict[str, Any],
    ) -> None:
        """
        Store the rendering intent without performing any work.

        Parameters
        ----------
        engine : orionis.view.contracts.engine.IViewEngine
            Engine used to render the template once awaited.
        template : str
            Template name using dot notation or a relative path.
        context : dict[str, typing.Any]
            Template variables forwarded to the engine.

        Returns
        -------
        None
            Store the rendering intent without performing any work.
        """
        self._engine: IViewEngine = engine
        """Engine used to render the template once awaited."""
        self._template: str = template
        """Template name using dot notation or a relative path."""
        self._context: dict[str, Any] = context
        """Template variables forwarded to the engine."""
        self._mutations: list[tuple[str, tuple, dict]] | None = None
        """Response changes queued while configuring the pending view."""
        self._flash: dict[str, Any] | None = None
        """Session values scheduled for availability during the next request."""

    def __getattr__(self: Self, name: str) -> Callable[..., PendingView]:
        """
        Queue a :class:`orionis.http.HTMLResponse` call to replay after rendering.

        Parameters
        ----------
        name : str
            Name of the response method being chained.

        Returns
        -------
        collections.abc.Callable[``...``, orionis.view.pending.PendingView]
            Callable that records the invocation and returns ``self``.

        Raises
        ------
        AttributeError
            If :class:`orionis.http.HTMLResponse` exposes no callable named *name*.
        """
        if not callable(getattr(HTMLResponse, name, None)):
            error_msg = f"'{type(self).__name__}' object has no attribute '{name}'"
            raise AttributeError(error_msg)  # noqa: TRY004

        def queue(*args: Any, **kwargs: Any) -> PendingView:
            """
            Store a response mutation until rendering completes.

            Parameters
            ----------
            *args : typing.Any
                Positional arguments for the response method.
            **kwargs : typing.Any
                Keyword arguments for the response method.

            Returns
            -------
            orionis.view.pending.PendingView
                The same pending view for fluent chaining.
            """
            mutations = self._mutations
            if mutations is None:
                mutations = self._mutations = []
            mutations.append((name, args, kwargs))
            return self

        return queue

    def __await__(self: Self) -> Generator[Any, None, HTMLResponse]:
        """
        Render the template and apply every queued mutation.

        Returns
        -------
        collections.abc.Generator[typing.Any, None, orionis.http.HTMLResponse]
            Generator yielding control until the response is ready.
        """
        return self.render().__await__()

    async def render(self: Self) -> HTMLResponse:
        """
        Render the template into a fully formed :class:`orionis.http.HTMLResponse`.

        Returns
        -------
        orionis.http.HTMLResponse
            An HTTP response whose body is the rendered HTML content.

        Raises
        ------
        orionis.view.exceptions.ViewTemplateNotFoundException
            When the view file cannot be located.
        orionis.view.exceptions.ViewRenderException
            When rendering fails for any reason.
        """
        if self._flash:
            await self.__flashToSession()

        try:
            response_html: str = await self._engine.render(
                self._template,
                self._context,
            )
            response = HTMLResponse(
                content=response_html,
                headers={
                    "X-Orionis-Render": "SSR",
                },
            )
        except ViewTemplateNotFoundException:
            # Missing templates keep their own type for the caller.
            raise
        except Exception as e:
            detail: str = _LOCALS_QUALNAME.sub("", str(e))
            exc_msg: str = f"Failed to render view '{self._template}': {detail}"
            error_msg = exc_msg
            raise ViewRenderException(error_msg) from e

        if self._mutations:
            for name, args, kwargs in self._mutations:
                getattr(response, name)(*args, **kwargs)

        return response

    async def __flashToSession(self: Self) -> None:
        """
        Write the queued flash data into the active session.

        Silently skips when no session is available, e.g. on routes
        without the session middleware.

        Returns
        -------
        None
            Write the queued flash data into the active session.
        """
        try:
            session: ISession = await Session.resolve()
        except Exception as error:
            from orionis.session.contracts.session import ISession  # noqa: PLC0415
            from orionis.view._failures import capture_service_failure  # noqa: PLC0415
            await capture_service_failure(error, ISession)
            return

        apply_flash(session, self._flash)
