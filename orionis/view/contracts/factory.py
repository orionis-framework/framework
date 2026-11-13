# ruff: noqa: ANN401, TC001
# Retain arbitrary template context and the public deferred-result runtime type.
"""Contract for the view factory."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from orionis.view.pending import PendingView


class IViewFactory(ABC):
    """
    Contract for the view factory.

    Callers receive a :class:`orionis.view.pending.PendingView` synchronously.
    Await that value to render a named template and obtain an
    :class:`orionis.http.HTMLResponse` ready to return from an HTTP controller.
    """

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

        Notes
        -----
        Template lookup and rendering errors are raised when the returned value
        is awaited, rather than when this method prepares it.
        """
