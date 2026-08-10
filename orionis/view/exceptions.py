from __future__ import annotations

class ViewException(Exception):
    """
    Base exception for all view-system errors.

    All specialised view exceptions inherit from this class, allowing
    callers to catch the entire view-exception hierarchy with a single
    ``except ViewException`` clause.
    """

class ViewRenderException(ViewException):
    """
    Raised when a template fails to render.

    Typically wraps a Jinja2 :class:`TemplateError` and preserves the
    original cause as the ``__cause__`` of the exception chain.
    """

class ViewTemplateNotFoundException(ViewException):
    """
    Raised when the requested template file cannot be located.

    Wraps a Jinja2 :class:`TemplateNotFound` and preserves the original
    cause as the ``__cause__`` of the exception chain.
    """

class ViewRouteException(ViewException):
    """
    Raised when the ``route()`` template global cannot build a URL.

    Signals either an unknown route name or a path parameter left
    without a value.
    """
