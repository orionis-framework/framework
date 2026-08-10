from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.http.adapters.request.contracts.transport import TransportAdapter
from orionis.http.payload.estructures.headers import Headers

if TYPE_CHECKING:
    from typing import Any

# Sentinel that marks per-request lazy fields as "not yet resolved"
_MISSING: Any = object()

class ASGITransportAdapter(TransportAdapter):
    """
    Adapt an ASGI scope dictionary to the transport adapter contract.

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
        "__raw_headers",
        "__scope",
        "__wants_json",
    )

    def __init__(self, scope: dict) -> None:
        """
        Initialize the adapter with an ASGI scope dictionary.

        Parameters
        ----------
        scope : dict
            Provide the ASGI scope mapping.

        Returns
        -------
        None
            Return ``None``.
        """
        # Store request scope and raw headers for fast repeated access.
        self.__scope: dict = scope
        self.__raw_headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
        # Keep all overrides and computed fields in one dictionary.
        self.__overrides: dict[str, Any] = {}
        # Lazily resolve expensive fields only when first requested.
        self.__client: Any = _MISSING
        self.__wants_json: Any = _MISSING
        # Build headers once since they are frequently read.
        self.__headers: Headers = self.__buildHeadersASGI()

    def __getitem__(self, key: str) -> object | None:
        """
        Get a cached override value by key.

        Parameters
        ----------
        key : str
            Specify the override key.

        Returns
        -------
        object | None
            Return the stored value, or ``None`` when absent.
        """
        # Read from override storage.
        return self.__overrides.get(key)

    def __setitem__(self, key: str, value: object) -> None:
        """
        Set a cached override value by key.

        Parameters
        ----------
        key : str
            Specify the override key.
        value : object
            Provide the value to store.

        Returns
        -------
        None
            Return ``None``.
        """
        # Write to override storage.
        self.__overrides[key] = value

    def __contains__(self, key: str) -> bool:
        """
        Check whether an override key exists.

        Parameters
        ----------
        key : str
            Specify the override key.

        Returns
        -------
        bool
            Return ``True`` when the key exists, else ``False``.
        """
        # Perform direct key-membership lookup.
        return key in self.__overrides

    def __delitem__(self, key: str) -> None:
        """
        Delete an override value by key.

        Parameters
        ----------
        key : str
            Specify the override key.

        Returns
        -------
        None
            Return ``None``.
        """
        # Remove key safely if present.
        self.__overrides.pop(key, None)

    def __buildHeadersASGI(self) -> Headers:
        """
        Build a ``Headers`` object from ASGI raw headers.

        Returns
        -------
        Headers
            Return decoded and indexed request headers.
        """
        # Decode raw byte pairs to latin-1 strings.
        return Headers([
            (k.decode("latin-1"), v.decode("latin-1"))
            for k, v in self.__raw_headers
        ])

    def client(self) -> str | None:
        """
        Get the remote client IP from the ASGI scope.

        Returns
        -------
        str | None
            Return the client IP, or ``None`` when unavailable.
        """
        # Return cached value when already resolved.
        c = self.__client
        if c is not _MISSING:
            return c

        # Read ASGI client tuple: (host, port) or None.
        raw = self.__scope.get("client")
        if not raw:
            self.__client = None
            return None

        ip: str = raw[0]
        self.__client = ip
        # Persist resolved client and port for merged scope reads.
        self.__overrides["client"] = ip
        self.__overrides["port"] = int(raw[1])
        return ip

    def setClient(self, ip: str) -> None:
        """
        Set the remote client address.

        Parameters
        ----------
        ip : str
            Provide the client IP value.

        Returns
        -------
        None
            Return ``None``.
        """
        # Keep override storage and cached slot synchronized.
        self.__overrides["client"] = ip
        self.__client = ip

    def scheme(self) -> str | None:
        """
        Get the URL scheme.

        Returns
        -------
        str | None
            Return the scheme, or ``None`` when missing.
        """
        # Prefer override value, then fallback to original scope.
        v = self.__overrides.get("scheme")
        return v if v is not None else self.__scope.get("scheme")

    def setScheme(self, value: str) -> None:
        """
        Set the URL scheme.

        Parameters
        ----------
        value : str
            Provide the scheme, such as ``"http"`` or ``"https"``.

        Returns
        -------
        None
            Return ``None``.
        """
        # Persist scheme override.
        self.__overrides["scheme"] = value

    def method(self) -> str | None:
        """
        Get the HTTP method.

        Returns
        -------
        str | None
            Return the HTTP method, or ``None`` when missing.
        """
        # Prefer override value, then fallback to original scope.
        v = self.__overrides.get("method")
        return v if v is not None else self.__scope.get("method")

    def path(self) -> str | None:
        """
        Get the request path.

        Returns
        -------
        str | None
            Return the request path, or ``None`` when missing.
        """
        # Read path directly from original scope.
        return self.__scope.get("path")

    def headers(self) -> Headers:
        """
        Get request headers.

        Returns
        -------
        Headers
            Return the prebuilt ``Headers`` instance.
        """
        # Return cached headers object built at initialization.
        return self.__headers

    def setState(self, key: str, value: Any) -> None:
        """
        Set an arbitrary override state value.

        Parameters
        ----------
        key : str
            Specify the key to set.
        value : Any
            Provide the value to store.

        Returns
        -------
        None
            Return ``None``.
        """
        # Store custom state in override mapping.
        self.__overrides[key] = value

    def wantsJson(self) -> bool:
        """
        Determine whether the client prefers JSON.

        Returns
        -------
        bool
            Return ``True`` when Accept includes JSON media types.
        """
        # Return cached decision when already computed.
        cached = self.__wants_json
        if cached is not _MISSING:
            return cached

        # Inspect Accept header once and cache result.
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
        Get the adjusted ASGI scope dictionary.

        Returns
        -------
        dict
            Return original scope merged with overrides.
        """
        # Fast path avoids allocation when there are no overrides.
        if not self.__overrides:
            return self.__scope

        # Merge scope and overrides into a new mapping.
        return {**self.__scope, **self.__overrides}
