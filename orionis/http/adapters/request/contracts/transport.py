from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any
    from orionis.http.payload.estructures.headers import Headers

class TransportAdapter(ABC):
    """
    Read/write abstraction over a protocol scope (ASGI or RSGI).

    Decouples middleware logic from the underlying transport protocol,
    allowing all middlewares to operate against a single unified
    interface regardless of whether the server speaks ASGI or RSGI.
    """

    # ruff: noqa: ANN401

    # Define the transport interface without instance state.
    __slots__ = ()

    @abstractmethod
    def client(self) -> str | None:
        """
        Return the remote client address parsed from the RSGI/ASGI scope.

        Returns
        -------
        str | None
            The client IP address as a string, or None if not available.
        """

    @abstractmethod
    def setClient(self, ip: str) -> None:
        """
        Set the remote client address in the scope.

        Parameters
        ----------
        ip : str
            The client IP address to assign.

        Returns
        -------
        None
            No value is returned.
        """

    @abstractmethod
    def scheme(self) -> str | None:
        """
        Return the URL scheme of the current request.

        Returns
        -------
        str | None
            The scheme (e.g. ``'http'``, ``'https'``), or None.
        """

    @abstractmethod
    def setScheme(self, value: str) -> None:
        """
        Set the URL scheme of the current request.

        Parameters
        ----------
        value : str
            The scheme to apply (e.g. ``'http'``, ``'https'``).

        Returns
        -------
        None
            No value is returned.
        """

    @abstractmethod
    def method(self) -> str | None:
        """
        Return the HTTP method of the current request.

        Returns
        -------
        str | None
            The HTTP method (e.g. ``'GET'``, ``'POST'``), or None.
        """

    @abstractmethod
    def path(self) -> str | None:
        """
        Return the URL path of the current request.

        Returns
        -------
        str | None
            The request path, or None if unavailable.
        """

    @abstractmethod
    def headers(self) -> Headers:
        """
        Return the request headers as a Headers object.

        Returns
        -------
        Headers
            The headers parsed from the scope, decoded to strings.
        """

    @abstractmethod
    def setState(self, key: str, value: Any) -> None:
        """
        Store an arbitrary value in the scope under the given key.

        Parameters
        ----------
        key : str
            The attribute or dict key to set.
        value : Any
            The value to store.

        Returns
        -------
        None
            No value is returned.
        """

    @abstractmethod
    def wantsJson(self) -> bool:
        """
        Determine if the client prefers a JSON response based on the Accept header.

        Returns
        -------
        bool
            True if the Accept header indicates JSON is preferred, otherwise False.
        """

    @abstractmethod
    def getScope(self) -> dict:
        """
        Return the underlying protocol scope object.

        Returns the scope as adjusted by the use of other methods in this adapter.
        Reflects any modifications made through setClient, setScheme, setState, etc.

        Returns
        -------
        dict
            A dict representation of the scope with any overrides applied.
            The original scope object is never mutated.
        """
