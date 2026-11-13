# ruff: noqa: ANN401, BLE001, TC001, TC003
# Keep public callback and application annotations resolvable at runtime.
# Preserve heterogeneous template payload values.
# Observe optional service failures centrally before returning a fallback.
"""Provide view globals operations.

Includes ``_split_scheme``, ``_request_base_url``, ``_absolute_url``,
``_to_secure_url``, and ``_global_url``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlencode

from orionis.foundation.contracts.application import IApplication
from orionis.http.contracts.request import IRequest
from orionis.view._failures import capture_service_failure


def _split_scheme(url: str) -> tuple[str, str]:
    """Split an explicit URL scheme without normalizing its remaining content.

    Parameters
    ----------
    url : str
        URL or path whose scheme may be followed by a colon and two slashes.

    Returns
    -------
    tuple[str, str]
        Lowercase scheme and exact remainder, or two empty strings when the
        separator is absent. This helper performs no URL validation.
    """
    scheme, separator, remainder = url.partition("://")
    return (scheme.lower(), remainder) if separator else ("", "")


async def _request_base_url(app: IApplication) -> str:
    """
    Return the base URL of the request currently in scope.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.

    Returns
    -------
    str
        Base URL without a trailing slash, or an empty string when no
        request is in scope.
    """
    try:
        request: IRequest = await app.make(IRequest)
    except Exception as error:
        await capture_service_failure(error, IRequest, app=app)
        return ""
    return request.baseUrl.rstrip("/")


async def _absolute_url(
    app: IApplication,
    path: str,
    query: dict[str, Any],
) -> str:
    """
    Build a URL from a path, prefixing the current request base URL.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.
    path : str
        HTTP(S), protocol-relative URL, or application-relative path.
    query : dict[str, typing.Any]
        Query string values appended to the resulting URL.

    Returns
    -------
    str
        Absolute URL when a request is in scope, otherwise the
        normalised path.
    """
    if path.startswith("//") or _split_scheme(path)[0] in ("http", "https"):
        base = ""
        target = path
    else:
        base = await _request_base_url(app)
        target = "/" + path.lstrip("/") if path else "/"

    if query:
        target, fragment_separator, fragment = target.partition("#")
        separator = "&" if "?" in target else "?"
        target = (
            f"{target}{separator}{urlencode(query, doseq=True)}"
            f"{fragment_separator}{fragment}"
        )

    return f"{base}{target}"


def _to_secure_url(url: str) -> str:
    """
    Rewrite an already built URL so it uses the HTTPS scheme.

    Parameters
    ----------
    url : str
        URL to normalize. Recognize HTTP schemes without regard to case.
        Preserve existing HTTPS URLs, other schemes, and relative paths.

    Returns
    -------
    str
        HTTPS URL for HTTP or protocol-relative inputs, with the remaining
        content unchanged. Return all other inputs without modification.
    """
    if url.startswith("//"):
        return f"https:{url}"
    scheme, remainder = _split_scheme(url)
    return f"https://{remainder}" if scheme == "http" else url


def _global_url(app: IApplication) -> Callable[..., Awaitable[str]]:
    """
    Build the async ``url`` template global bound to the application.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.

    Returns
    -------
    collections.abc.Callable
        Async callable that builds a URL from a path.
    """

    async def url(path: str = "/", **query: Any) -> str:
        """
        Build a URL for an application path.

        Parameters
        ----------
        path : str, optional
            Application-relative path, or an HTTP(S) or protocol-relative
            URL returned untouched apart from added query arguments.
        **query : typing.Any
            Values encoded as the query string of the URL.

        Returns
        -------
        str
            Absolute URL when a request is in scope, otherwise the
            normalised path.
        """
        return await _absolute_url(app, path, query)

    return url


def _global_secure_url(app: IApplication) -> Callable[..., Awaitable[str]]:
    """
    Build the async ``secure_url`` template global bound to the application.

    Parameters
    ----------
    app : orionis.IApplication
        Application container used for service resolution.

    Returns
    -------
    collections.abc.Callable
        Async callable that builds an HTTPS URL from a path.
    """

    async def secure_url(path: str = "/", **query: Any) -> str:
        """
        Build an HTTPS URL for an application path.

        Parameters
        ----------
        path : str, optional
            Application-relative path, or an HTTP(S) or protocol-relative
            URL whose insecure HTTP scheme is upgraded to HTTPS.
        **query : typing.Any
            Values encoded as the query string of the URL.

        Returns
        -------
        str
            HTTPS URL when a host is known, otherwise the normalised
            path.
        """
        return _to_secure_url(await _absolute_url(app, path, query))

    return secure_url
