from __future__ import annotations
import re
from collections.abc import Mapping
from typing import Any, TYPE_CHECKING
from orionis.http.response import HTMLResponse
from orionis.support.facades.session import Session
from orionis.view.exceptions import ViewRenderException, ViewTemplateNotFoundException

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from orionis.session.contracts.session import ISession
    from orionis.view.contracts.engine import IViewEngine

# Closure qualname noise (e.g. ``_global_csrf_field.<locals>.``) leaked by
# errors raised inside template globals; irrelevant for the developer.
_LOCALS_QUALNAME = re.compile(r"[\w.]*<locals>\.") # NOSONAR

class PendingView:
    """
    Awaitable, chainable result of :meth:`IViewFactory.make`.

    Rendering is deferred until the object is awaited, so response
    mutators such as ``withFlash()`` or ``withCookie()`` can be chained
    directly on the ``make()`` call::

        return await View.make("auth.login").withFlash("email", email)

    Every attribute that exists on :class:`HTMLResponse` is accepted and
    replayed on the real response once the template has been rendered.
    """

    # ruff: noqa: ANN401, BLE001

    __slots__ = ("_context", "_engine", "_flash", "_mutations", "_template")

    def __init__(
        self,
        engine: IViewEngine,
        template: str,
        context: dict[str, Any],
    ) -> None:
        """
        Store the rendering intent without performing any work.

        Parameters
        ----------
        engine : IViewEngine
            Engine used to render the template once awaited.
        template : str
            Template name using dot notation or a relative path.
        context : dict[str, Any]
            Template variables forwarded to the engine.

        Returns
        -------
        None
        """
        self._engine: IViewEngine = engine
        self._template: str = template
        self._context: dict[str, Any] = context
        self._mutations: list[tuple[str, tuple, dict]] | None = None
        self._flash: dict[str, Any] | None = None

    def withFlash(
        self,
        key: str | Mapping[str, Any],
        value: Any = None,
    ) -> PendingView:
        """
        Flash data into the session before the template is rendered.

        Writing happens ahead of rendering so the very same view can read
        the values back through the ``old()`` global, and they remain
        available for the next request as regular flash data.

        Parameters
        ----------
        key : str | Mapping[str, Any]
            Flash data key, or a mapping of several key-value pairs.
        value : Any, optional
            Value to flash when *key* is a plain key.

        Returns
        -------
        PendingView
            The same pending view, allowing fluent chaining.
        """
        flash = self._flash
        if flash is None:
            flash = self._flash = {}

        if isinstance(key, Mapping):
            flash.update(key)
        else:
            flash[key] = value

        return self

    def __getattr__(self, name: str) -> Callable[..., PendingView]:
        """
        Queue a :class:`HTMLResponse` call to replay after rendering.

        Parameters
        ----------
        name : str
            Name of the response method being chained.

        Returns
        -------
        Callable[..., PendingView]
            Callable that records the invocation and returns ``self``.

        Raises
        ------
        AttributeError
            If :class:`HTMLResponse` exposes no callable named *name*.
        """
        if not callable(getattr(HTMLResponse, name, None)):
            error_msg = (
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
            raise AttributeError(error_msg)  # noqa: TRY004

        def queue(*args: Any, **kwargs: Any) -> PendingView:
            mutations = self._mutations
            if mutations is None:
                mutations = self._mutations = []
            mutations.append((name, args, kwargs))
            return self

        return queue

    def __await__(self) -> Generator[Any, None, HTMLResponse]:
        """
        Render the template and apply every queued mutation.

        Returns
        -------
        Generator[Any, None, HTMLResponse]
            Generator yielding control until the response is ready.
        """
        return self.render().__await__()

    async def render(self) -> HTMLResponse:
        """
        Render the template into a fully formed :class:`HTMLResponse`.

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
            raise ViewRenderException(exc_msg) from e

        if self._mutations:
            for name, args, kwargs in self._mutations:
                getattr(response, name)(*args, **kwargs)

        return response

    async def __flashToSession(self) -> None:
        """
        Write the queued flash data into the active session.

        Silently skips when no session is available, e.g. on routes
        without the session middleware.

        Returns
        -------
        None
        """
        try:
            session: ISession = await Session.resolve()
        except Exception:
            return

        for key, value in self._flash.items():
            session.flash(key, value)
