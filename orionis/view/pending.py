# ruff: noqa: ANN401, BLE001, PLC0415, PLR0913, TC001, TC003, TRY004
# Preserve dynamic response arguments, runtime types and attribute protocol errors.
# Observe resolution failures through the lazily imported central failure service.
"""Provide awaitable, chainable results of template rendering."""

from __future__ import annotations
import re
from collections.abc import Callable, Generator, Mapping
from typing import Any, Self
from orionis.background.task import BackgroundTask
from orionis.http.enums.status import HTTPStatus
from orionis.http.responses import HTMLResponse
from orionis.session.contracts.session import ISession
from orionis.session.flash import _FlashData, apply_flash
from orionis.support.concurrency import WorkQueueFullError
from orionis.support.facades.session import Session
from orionis.view.exceptions import ViewRenderException, ViewTemplateNotFoundException
from orionis.view.contracts.engine import IViewEngine

# Closure qualname noise (e.g. ``_global_csrf_field.<locals>.``) leaked by
# errors raised inside template globals; irrelevant for the developer.
# Start at a qualifier boundary to avoid rescanning every suffix of long messages.
# Consume adjacent nested qualifiers together to preserve the original output.
_LOCALS_QUALNAME = re.compile(r"(?<![\w.])(?:[\w.]*<locals>\.)+")
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

    Callable attributes on :class:`orionis.http.HTMLResponse` are accepted and
    replayed on the real response once the template has been rendered. Initial
    response options are applied before queued mutations, in call order.
    """

    __slots__ = (
        "_background",
        "_context",
        "_engine",
        "_flash",
        "_headers",
        "_mutations",
        "_status_code",
        "_template",
    )
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self: Self,
        engine: IViewEngine,
        template: str,
        context: dict[str, Any],
        *,
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
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
        status_code : orionis.http.enums.HTTPStatus | int, optional
            HTTP status code for the rendered response.
        headers : collections.abc.Mapping[str, str] | None, optional
            Response headers. The SSR marker is added when not supplied.
        background : orionis.background.BackgroundTask | None, optional
            Task to run after the response is sent.

        Returns
        -------
        None
            No return value.
        """
        self._engine: IViewEngine = engine
        """Engine used to render the template once awaited."""
        self._template: str = template
        """Template name using dot notation or a relative path."""
        self._context: dict[str, Any] = context
        """Template variables forwarded to the engine."""
        self._status_code: HTTPStatus | int = status_code
        """Initial HTTP status code, validated when the view is rendered."""
        self._headers: Mapping[str, str] | None = headers
        """Initial response headers, separate from template variables."""
        self._background: BackgroundTask | None = background
        """Initial background task, executed only after response delivery."""
        self._mutations: list[tuple[str, tuple, dict]] | None = None
        """Response changes queued while configuring the pending view."""
        self._flash: dict[str, Any] | None = None
        """Session values scheduled for availability during the next request."""

    def withStatusCode(self: Self, status_code: HTTPStatus | int) -> Self:
        """
        Queue an HTTP status change and return the pending view.

        Parameters
        ----------
        status_code : orionis.http.enums.HTTPStatus | int
            HTTP status code, validated when the view is awaited.

        Returns
        -------
        Self
            The same pending view for fluent chaining.
        """
        return self.__queueMutation("withStatusCode", status_code)

    def withHeaders(self: Self, headers: Mapping[str, str]) -> Self:
        """
        Queue response headers and return the pending view.

        Parameters
        ----------
        headers : collections.abc.Mapping[str, str]
            Headers to merge, replacing matching names without regard to case.
            Unrelated headers remain unchanged.

        Returns
        -------
        Self
            The same pending view for fluent chaining.
        """
        return self.__queueMutation("withHeaders", headers)

    def withBackground(self: Self, background: BackgroundTask | None) -> Self:
        """
        Queue a background task change and return the pending view.

        Parameters
        ----------
        background : orionis.background.BackgroundTask | None
            Task to run after delivery, or ``None`` to clear the current task.
            Validated when the view is awaited.

        Returns
        -------
        Self
            The same pending view for fluent chaining.
        """
        return self.__queueMutation("withBackground", background)

    def __queueMutation(
        self: Self,
        name: str,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Self:
        """
        Retain a response mutation in call order without rendering.

        Parameters
        ----------
        name : str
            Name of the response method to invoke after rendering.
        *args : typing.Any
            Positional arguments for the response method.
        **kwargs : typing.Any
            Keyword arguments for the response method.

        Returns
        -------
        Self
            The same pending view for fluent chaining.
        """
        mutations = self._mutations
        if mutations is None:
            mutations = self._mutations = []
        mutations.append((name, args, kwargs))
        return self

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
            raise AttributeError(error_msg)

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
            return self.__queueMutation(name, *args, **kwargs)

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
        orionis.support.concurrency.WorkQueueFullError
            When the engine's template loading workers are saturated.
        TypeError
            When response options have incompatible types.
        ValueError
            When a response status code is outside the supported range.
        """
        if self._flash:
            await self.__flashToSession()

        try:
            response_html: str = await self._engine.render(
                self._template,
                self._context,
            )
        except ViewTemplateNotFoundException, ViewRenderException, WorkQueueFullError:
            # Preserve the engine's classified failure and original cause.
            raise
        except Exception as e:
            detail: str = _LOCALS_QUALNAME.sub("", str(e))
            exc_msg: str = f"Failed to render view '{self._template}': {detail}"
            error_msg = exc_msg
            raise ViewRenderException(error_msg) from e

        # Keep response validation separate from template rendering failures.
        response = HTMLResponse(
            content=response_html,
            status_code=self._status_code,
            headers=self._headers,
            background=self._background,
        )
        if not response.hasHeader("x-orionis-render"):
            response.setHeader("X-Orionis-Render", "SSR")

        if self._mutations:
            for name, args, kwargs in self._mutations:
                getattr(response, name)(*args, **kwargs)

        return response

    async def __flashToSession(self: Self) -> None:
        """
        Write the queued flash data into the active session.

        Skip writes when the session is unavailable, such as on routes without
        session middleware, and centrally observe unexpected resolution failures.

        Returns
        -------
        None
            No return value.
        """
        try:
            session: ISession = await Session.resolve()
        except Exception as error:
            from orionis.view._failures import capture_service_failure

            await capture_service_failure(error, ISession)
            return

        apply_flash(session, self._flash)
