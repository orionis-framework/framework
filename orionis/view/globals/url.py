from __future__ import annotations
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode
from orionis.http.contracts.request import IRequest

if TYPE_CHECKING:
    from orionis.foundation.contracts.application import IApplication

# ruff: noqa: ANN401, BLE001

# Prefixes identifying an already absolute URL.
_ABSOLUTE_PREFIXES: tuple[str, ...] = ("http://", "https://", "//")  # NOSONAR

# Scheme prefixes rewritten by the ``secure_*`` template globals.
_INSECURE_PREFIX: str = "http://"  # NOSONAR
_SECURE_PREFIX: str = "https://"
_SCHEMELESS_PREFIX: str = "//"

async def _request_base_url(app: IApplication) -> str:
    """
    Return the base URL of the request currently in scope.

    Parameters
    ----------
    app : IApplication
        Application container used for service resolution.

    Returns
    -------
    str
        Base URL without a trailing slash, or an empty string when no
        request is in scope.
    """
    try:
        request: IRequest = await app.make(IRequest)
    except Exception:
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
    app : IApplication
        Application container used for service resolution.
    path : str
        Absolute URL or application-relative path.
    query : dict[str, Any]
        Query string values appended to the resulting URL.

    Returns
    -------
    str
        Absolute URL when a request is in scope, otherwise the
        normalised path.
    """
    if path.startswith(_ABSOLUTE_PREFIXES):
        base = ""
        target = path
    else:
        base = await _request_base_url(app)
        target = "/" + path.lstrip("/") if path else "/"

    if query:
        separator = "&" if "?" in target else "?"
        target = f"{target}{separator}{urlencode(query, doseq=True)}"

    return f"{base}{target}"

def _to_secure_url(url: str) -> str:
    """
    Rewrite an already built URL so it uses the HTTPS scheme.

    Parameters
    ----------
    url : str
        URL to normalise. Relative paths and HTTPS URLs are returned
        untouched, since no host can be inferred for the former.

    Returns
    -------
    str
        URL served over HTTPS whenever a host is present.
    """
    if url.startswith(_INSECURE_PREFIX):
        return url.replace(_INSECURE_PREFIX, _SECURE_PREFIX, 1)
    if url.startswith(_SCHEMELESS_PREFIX):
        return url.replace(_SCHEMELESS_PREFIX, _SECURE_PREFIX, 1)
    return url

def _global_url(app: IApplication) -> Any:
    """
    Build the async ``url`` template global bound to the application.

    Parameters
    ----------
    app : IApplication
        Application container used for service resolution.

    Returns
    -------
    Any
        Async callable that builds a URL from a path.
    """
    async def url(path: str = "/", **query: Any) -> str:
        """
        Build a URL for an application path.

        Parameters
        ----------
        path : str, optional
            Application-relative path, or an already absolute URL, which
            is returned untouched apart from the query string.
        **query : Any
            Values encoded as the query string of the URL.

        Returns
        -------
        str
            Absolute URL when a request is in scope, otherwise the
            normalised path.
        """
        return await _absolute_url(app, path, query)

    return url

def _global_secure_url(app: IApplication) -> Any:
    """
    Build the async ``secure_url`` template global bound to the application.

    Parameters
    ----------
    app : IApplication
        Application container used for service resolution.

    Returns
    -------
    Any
        Async callable that builds an HTTPS URL from a path.
    """
    async def secure_url(path: str = "/", **query: Any) -> str:
        """
        Build an HTTPS URL for an application path.

        Parameters
        ----------
        path : str, optional
            Application-relative path, or an already absolute URL, whose
            scheme is forced to HTTPS.
        **query : Any
            Values encoded as the query string of the URL.

        Returns
        -------
        str
            HTTPS URL when a host is known, otherwise the normalised
            path.
        """
        return _to_secure_url(await _absolute_url(app, path, query))

    return secure_url
