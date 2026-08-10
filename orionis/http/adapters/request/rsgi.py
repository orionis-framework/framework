from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.http.adapters.request.contracts.transport import TransportAdapter
from orionis.http.payload.estructures.headers import Headers

if TYPE_CHECKING:
    from typing import Any
    from granian.rsgi import Scope

# Sentinel that marks per-request lazy fields as "not yet resolved"
_MISSING: Any = object()

class RSGITransportAdapter(TransportAdapter):
    """
    Adapt a Granian RSGI scope to the transport adapter contract.

    Returns
    -------
    None
        This class exposes request data accessors and state overrides.
    """

    # ruff: noqa: ANN401

    # Slots eliminate the per-instance __dict__, replacing hash-based dict
    # lookups with direct indexed slot access for all hot-path attributes
    __slots__ = (
        "__client",
        "__headers",
        "__overrides",
        "__scope",
        "__wants_json",
    )

    def __init__(self, scope: Scope) -> None:
        """
        Initialize the adapter with a Granian RSGI scope.

        Parameters
        ----------
        scope : Scope
            The Granian RSGI scope object.

        Returns
        -------
        None
            Return ``None`` after preparing internal caches and state.
        """
        # Store the original RSGI scope object.
        self.__scope: Scope = scope
        # Keep overrides and computed values in a single state dictionary.
        self.__overrides: dict[str, Any] = {}
        # Resolve lazy fields on first access using the _MISSING sentinel.
        self.__client: Any = _MISSING
        self.__wants_json: Any = _MISSING
        # Build headers once because they are read frequently.
        self.__headers: Headers = self.__buildHeadersRSGI()

    def __getitem__(self, key: str) -> object | None:
        """
        Return a cached state value by key.

        Parameters
        ----------
        key : str
            The key to look up in the cache.

        Returns
        -------
        object | None
            Return the stored value when present, otherwise ``None``.
        """
        # Read from the override/state store.
        return self.__overrides.get(key)

    def __setitem__(self, key: str, value: object) -> None:
        """
        Store a state value under a key.

        Parameters
        ----------
        key : str
            The key under which to store the value.
        value : object
            The value to store in the cache.

        Returns
        -------
        None
            Return ``None`` after writing the value.
        """
        # Write into the override/state store.
        self.__overrides[key] = value

    def __contains__(self, key: str) -> bool:
        """
        Check whether a state key exists.

        Parameters
        ----------
        key : str
            The key to check for existence in the cache.

        Returns
        -------
        bool
            Return ``True`` when the key exists, otherwise ``False``.
        """
        # Test membership in the override/state store.
        return key in self.__overrides

    def __delitem__(self, key: str) -> None:
        """
        Remove a state value by key.

        Parameters
        ----------
        key : str
            The key to remove from the cache.

        Returns
        -------
        None
            Return ``None`` after removing the key when present.
        """
        # Remove from the override/state store if present.
        self.__overrides.pop(key, None)

    def __buildHeadersRSGI(self) -> Headers:
        """
        Build headers from the scope and cache them.

        Returns
        -------
        Headers
            Return parsed headers as lowercase name/value pairs.
        """
        # Cache scope headers reference to avoid repeated attribute access.
        scope_headers = self.__scope.headers
        # Flatten multi-value headers into lowercase key/value tuples.
        raw: list[tuple[str, str]] = [
            (str(key).lower(), value)
            for key in scope_headers
            for value in scope_headers.get_all(key)
        ]
        return Headers(raw)

    def client(self) -> str | None:
        """
        Return the remote client IP parsed from the scope.

        Returns
        -------
        str | None
            Return the client IP string, or ``None`` when unavailable.
        """
        # Return cached result on subsequent calls.
        c = self.__client
        if c is not _MISSING:
            return c

        raw = self.__scope.client
        if not raw:
            self.__client = None
            return None

        # Parse host and port, including IPv6 forms with multiple colons.
        if raw.count(":") > 1:
            ip, port = raw.rsplit(":", 1)
        else:
            ip, port = raw.split(":", 1)

        self.__client = ip
        # Expose resolved client data through the state layer.
        self.__overrides["client"] = ip
        self.__overrides["port"] = int(port)
        return ip

    def setClient(self, ip: str) -> None:
        """
        Set the remote client IP in the override state.

        Parameters
        ----------
        ip : str
            The client IP address to assign.

        Returns
        -------
        None
            Return ``None`` after updating the cached client value.
        """
        # Update both override state and the fast-access cached slot.
        self.__overrides["client"] = ip
        self.__client = ip

    def scheme(self) -> str | None:
        """
        Return the request scheme.

        Returns
        -------
        str | None
            Return the override value when set, else the scope scheme.
        """
        # Prefer override value and fall back to scope data.
        v = self.__overrides.get("scheme")
        return v if v is not None else self.__scope.scheme

    def setScheme(self, value: str) -> None:
        """
        Set the request scheme in the override state.

        Parameters
        ----------
        value : str
            The scheme to apply (e.g. ``'http'``, ``'https'``).

        Returns
        -------
        None
            Return ``None`` after storing the scheme override.
        """
        # Persist the scheme override in state.
        self.__overrides["scheme"] = value

    def method(self) -> str | None:
        """
        Return the HTTP method.

        Returns
        -------
        str | None
            Return the override value when set, else the scope method.
        """
        # Prefer override value and fall back to scope data.
        v = self.__overrides.get("method")
        return v if v is not None else self.__scope.method

    def path(self) -> str | None:
        """
        Return the request path.

        Returns
        -------
        str | None
            Return the scope path value, which can be ``None``.
        """
        # Read path directly from the scope.
        return self.__scope.path

    def headers(self) -> Headers:
        """
        Return parsed request headers.

        Returns
        -------
        Headers
            Return the cached ``Headers`` instance built at initialization.
        """
        # Return the cached headers object.
        return self.__headers

    def setState(self, key: str, value: Any) -> None:
        """
        Store a custom value in the override state.

        Parameters
        ----------
        key : str
            The attribute name to set.
        value : Any
            The value to store.

        Returns
        -------
        None
            Return ``None`` after writing the state entry.
        """
        # Store arbitrary state in the override layer.
        self.__overrides[key] = value

    def wantsJson(self) -> bool:
        """
        Determine whether the request prefers a JSON response.

        Returns
        -------
        bool
            Return ``True`` when the Accept header indicates JSON support.
        """
        # Return cached result on subsequent calls.
        cached = self.__wants_json
        if cached is not _MISSING:
            return cached

        # Inspect Accept once and cache the result.
        accept = self.__headers.get("accept")
        if not accept:
            result = False
        else:
            lower = accept.lower()
            result = "application/json" in lower or "+json" in lower

        self.__wants_json = result
        return result

    def getScope(self) -> dict:
        """
        Build and return a dictionary view of the request scope.

        Returns
        -------
        dict
            Return base scope fields merged with override values.
        """
        # Cache scope reference to reduce repeated attribute lookups.
        scope = self.__scope
        base: dict[str, Any] = {
            "proto": scope.proto,
            "http_version": scope.http_version,
            "rsgi_version": scope.rsgi_version,
            "server": scope.server,
            "client": scope.client,
            "scheme": scope.scheme,
            "method": scope.method,
            "path": scope.path,
            "query_string": scope.query_string,
            "authority": scope.authority,
            "headers": scope.headers,
        }
        if self.__overrides:
            base.update(self.__overrides)
        return base
