from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Literal, Self, TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from collections.abc import AsyncIterable, Mapping

class IResponse(ABC):

    # ruff: noqa: PLR0913, ANN401

    __slots__ = ()

    @abstractmethod
    def render(self, content: Any) -> bytes:
        """
        Render the content to bytes.

        Parameters
        ----------
        content : Any
            The content to render.

        Returns
        -------
        bytes
            The rendered content as bytes.
        """

    @abstractmethod
    def addHeader(self, key: str, value: str) -> None:
        """
        Add a header to the response.

        Parameters
        ----------
        key : str
            The header name.
        value : str
            The header value.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def setHeader(self, key: str, value: str) -> None:
        """
        Set a header, replacing any existing values.

        Parameters
        ----------
        key : str
            The header name.
        value : str
            The header value.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def getHeader(self, key: str) -> list[str] | None:
        """
        Get the values for a header.

        Parameters
        ----------
        key : str
            The header name.

        Returns
        -------
        list[str] | None
            The list of header values, or None if not present.
        """

    @abstractmethod
    def hasHeader(self, key: str) -> bool:
        """
        Check if a header is present.

        Parameters
        ----------
        key : str
            The header name.

        Returns
        -------
        bool
            True if the header is present, False otherwise.
        """

    @abstractmethod
    def removeHeader(self, key: str) -> None:
        """
        Remove a header from the response.

        Parameters
        ----------
        key : str
            The header name.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def getRawHeaders(self) -> list[tuple[bytes, bytes]]:
        """
        Return the headers as a list of (key, value) byte tuples.

        Returns
        -------
        list of tuple of (bytes, bytes)
            The headers as (key, value) pairs encoded in latin-1.
        """

    @abstractmethod
    def setCookie(
        self,
        key: str,
        value: str = "",
        *,
        max_age: int | None = None,
        expires: datetime | str | int | None = None,
        path: str | None = "/",
        domain: str | None = None,
        secure: bool = False,
        http_only: bool = False,
        same_site: Literal["lax", "strict", "none"] | None = "lax",
        partitioned: bool = False,
    ) -> None:
        """
        Set a cookie header in the response.

        Parameters
        ----------
        key : str
            The cookie name.
        value : str, optional
            The cookie value. Defaults to an empty string.
        max_age : int | None, optional
            The maximum age of the cookie in seconds.
        expires : datetime | str | int | None, optional
            The expiration date of the cookie.
        path : str | None, optional
            The path for which the cookie is valid.
        domain : str | None, optional
            The domain for which the cookie is valid.
        secure : bool, optional
            Whether the cookie is secure.
        http_only : bool, optional
            Whether the cookie is HTTP only.
        same_site : str | None, optional
            The SameSite policy for the cookie.
        partitioned : bool, optional
            Whether the cookie is partitioned.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def deleteCookie(
        self,
        key: str,
        *,
        path: str = "/",
        domain: str | None = None,
    ) -> None:
        """
        Delete a cookie by setting its expiration to the past.

        Parameters
        ----------
        key : str
            The name of the cookie to delete.
        path : str, default="/"
            The path for which the cookie is valid.
        domain : str | None, optional
            The domain for which the cookie is valid.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def withCookie(
        self,
        key: str,
        value: str = "",
        *,
        max_age: int | None = None,
        expires: datetime | str | int | None = None,
        path: str | None = "/",
        domain: str | None = None,
        secure: bool = False,
        http_only: bool = False,
        same_site: Literal["lax", "strict", "none"] | None = "lax",
        partitioned: bool = False,
    ) -> Self:
        """
        Attach a cookie and return the response for chaining.

        Parameters
        ----------
        key : str
            The cookie name.
        value : str, optional
            The cookie value. Defaults to an empty string.
        max_age : int | None, optional
            The maximum age of the cookie in seconds.
        expires : datetime | str | int | None, optional
            The expiration date of the cookie.
        path : str | None, optional
            The path for which the cookie is valid.
        domain : str | None, optional
            The domain for which the cookie is valid.
        secure : bool, optional
            Whether the cookie is secure.
        http_only : bool, optional
            Whether the cookie is HTTP only.
        same_site : str | None, optional
            The SameSite policy for the cookie.
        partitioned : bool, optional
            Whether the cookie is partitioned.

        Returns
        -------
        Self
            The same response instance, allowing fluent chaining.
        """

    @abstractmethod
    def withCookies(
        self,
        cookies: Mapping[str, str | Mapping[str, Any]],
    ) -> Self:
        """
        Attach several cookies at once and return the response.

        Parameters
        ----------
        cookies : Mapping[str, str | Mapping[str, Any]]
            Mapping of cookie names to either a plain value or a mapping of
            keyword arguments accepted by :meth:`setCookie`.

        Returns
        -------
        Self
            The same response instance, allowing fluent chaining.
        """

    @abstractmethod
    def withoutCookie(
        self,
        key: str,
        *,
        path: str = "/",
        domain: str | None = None,
    ) -> Self:
        """
        Expire a cookie and return the response for chaining.

        Parameters
        ----------
        key : str
            The name of the cookie to delete.
        path : str, default="/"
            The path for which the cookie is valid.
        domain : str | None, optional
            The domain for which the cookie is valid.

        Returns
        -------
        Self
            The same response instance, allowing fluent chaining.
        """

    @abstractmethod
    def withFlash(
        self,
        key: str | Mapping[str, Any],
        value: Any = None,
    ) -> Self:
        """
        Flash data into the session and return the response for chaining.

        Parameters
        ----------
        key : str | Mapping[str, Any]
            Flash data key, or a mapping of several key-value pairs.
        value : Any, optional
            Value to flash when *key* is a plain key.

        Returns
        -------
        Self
            The same response instance, allowing fluent chaining.
        """

    @abstractmethod
    def getFlashData(self) -> dict[str, Any] | None:
        """
        Return the data queued by ``withFlash()`` for the session flash bag.

        Returns
        -------
        dict[str, Any] | None
            The queued key-value pairs, or None when nothing was queued.
        """

    @abstractmethod
    def getBody(self) -> bytes | None:
        """
        Return the response body as bytes.

        Returns
        -------
        bytes | None
            The response body as bytes, or None if not set.
        """

    @abstractmethod
    def getStream(self) -> AsyncIterable[bytes] | None:
        """
        Return the response stream if present.

        Returns
        -------
        AsyncIterable[bytes] | None
            The response stream, or None if not set.
        """

    @abstractmethod
    def hasStream(self) -> bool:
        """
        Check if the response has a stream.

        Returns
        -------
        bool
            True if a stream is present, False otherwise.
        """

    @abstractmethod
    async def runBackground(self) -> None:
        """
        Run the background task if it exists.

        Returns
        -------
        None
            This method does not return a value.
        """

    @abstractmethod
    def getStatusCode(self) -> int:
        """
        Return the HTTP status code of the response.

        Returns
        -------
        int
            The HTTP status code.
        """

    @abstractmethod
    def getMediaType(self) -> str | None:
        """
        Return the media type of the response.

        Returns
        -------
        str | None
            The media type, or None if not set.
        """
