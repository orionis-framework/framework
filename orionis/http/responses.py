from __future__ import annotations
import asyncio
import json
import mimetypes
from collections.abc import AsyncIterable, Iterable, Mapping, MutableMapping
from datetime import UTC, date, datetime, time
from decimal import Decimal
from email.utils import format_datetime
from enum import Enum
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, ClassVar, Literal, Self, TYPE_CHECKING
from urllib.parse import quote
from uuid import UUID
import msgspec.json as _msgspec_json
from orionis.http.contracts.response import IResponse
from orionis.background.task import BackgroundTask
from orionis.session.flash import (
    ERRORS_KEY,
    OLD_INPUT_KEY,
    filter_input,
    normalize_errors,
    queue_bag,
)

if TYPE_CHECKING:
    from orionis.http.enums.status import HTTPStatus

class Response(IResponse):

    # ruff: noqa: ANN401, C901, PLR0913, PLR2004

    __slots__ = (
        "_body",
        "_flash",
        "_headers",
        "_stream",
        "background",
        "media_type",
        "status_code",
    )

    # Shared constant avoids per-instance allocation; always UTF-8
    charset: ClassVar[str] = "utf-8"

    def __init__( # NOSONAR
        self,
        content: Any = None,
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        """
        Initialize the BaseResponse object.

        Parameters
        ----------
        content : Any, optional
            The response content or stream.
        status_code : HTTPStatus | int, optional
            The HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            The headers to include in the response.
        media_type : str | None, optional
            The media type of the response.
        background : BackgroundTask | None, optional
            The background task to run after response.

        Returns
        -------
        None
            This method does not return a value.
        """
        if not isinstance(status_code, int):
            error_msg = "status_code must be an integer"
            raise TypeError(error_msg)

        if not 100 <= status_code <= 599:
            error_msg = "status_code must be between 100 and 599"
            raise ValueError(error_msg)

        self.status_code = status_code
        self.media_type = media_type

        self._body: bytes | None = None
        self._stream: AsyncIterable[bytes] | None = None

        # Lazily allocated; most responses never flash anything
        self._flash: dict[str, Any] | None = None

        # Duck-type check avoids ABC registry traversal on every request
        if hasattr(content, "__aiter__"):
            self._stream = content
        else:
            self._body = self.render(content)

        self._headers: MutableMapping[str, list[str]] = {}

        if headers:
            # Plain dicts skip the ABC instance check on the response hot path
            if type(headers) is not dict and not isinstance(headers, Mapping):
                error_msg = "headers must be a mapping"
                raise TypeError(error_msg)

            store = self._headers
            for key, value in headers.items():
                key_lower = key.lower()
                existing = store.get(key_lower)
                if existing is None:
                    store[key_lower] = [value]
                else:
                    existing.append(value)

        if background is not None and not isinstance(background, BackgroundTask):
            error_msg = "background must be a BackgroundTask or None"
            raise TypeError(error_msg)

        self.background = background

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
        if content is None:
            return b""

        # Identity check skips MRO traversal and avoids a needless copy
        if type(content) is bytes:
            return content
        if isinstance(content, (bytearray, memoryview)):
            return bytes(content)

        if isinstance(content, str):
            return content.encode(self.charset)

        return str(content).encode(self.charset)

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
        key_lower = key.lower()
        # Avoid allocating an empty list when the key already exists
        headers = self._headers
        existing = headers.get(key_lower)
        if existing is None:
            headers[key_lower] = [value]
        else:
            existing.append(value)

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
        self._headers[key.lower()] = [value]

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
        return self._headers.get(key.lower())

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
        return key.lower() in self._headers

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
        self._headers.pop(key.lower(), None)

    def getRawHeaders(self) -> list[tuple[bytes, bytes]]:
        """
        Return the headers as a list of (key, value) byte tuples.

        Returns
        -------
        list of tuple of (bytes, bytes)
            The headers as (key, value) pairs encoded in latin-1.
        """
        # Flat comprehension eliminates intermediate list and generator allocations
        return [
            (key.encode("latin-1"), value.encode("latin-1"))
            for key, values in self._headers.items()
            for value in values
        ]

    def getStringHeaders(self) -> list[tuple[str, str]]:
        """
        Return the headers as a list of (key, value) string tuples.

        Returns
        -------
        list of tuple of str
            The headers represented as (key, value) string pairs.
        """
        return [
            (key, value)
            for key, values in self._headers.items()
            for value in values
        ]

    def setCookie( # NOSONAR
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
        cookie = SimpleCookie()
        cookie[key] = ""
        morsel = cookie[key]

        # Percent-encode the value ourselves: SimpleCookie would otherwise
        # wrap values containing characters such as '@' in double quotes.
        morsel.set(key, value, quote(value, safe=""))

        if max_age is not None:
            morsel["max-age"] = str(max_age)

        if isinstance(expires, datetime):
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            expires = format_datetime(
                expires.astimezone(UTC),
                usegmt=True,
            )

        if expires is not None:
            morsel["expires"] = str(expires)

        if path:
            morsel["path"] = path

        if domain:
            morsel["domain"] = domain

        if same_site is not None:
            s = same_site.lower()
            if s not in {"lax", "strict", "none"}:
                error_msg = (
                    "same_site must be 'lax', 'strict' or 'none'"
                )
                raise ValueError(error_msg)
            if s == "none" and not secure:
                error_msg = "SameSite=None requires secure=True"
                raise ValueError(error_msg)
            morsel["samesite"] = s

        if secure:
            morsel["secure"] = True

        if http_only:
            morsel["httponly"] = True

        if partitioned:
            morsel["partitioned"] = True

        cookie_value = cookie.output(header="").strip()
        self.addHeader("set-cookie", cookie_value)

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
        self.setCookie(
            key,
            max_age=0,
            expires=datetime(1970, 1, 1, tzinfo=UTC),
            path=path,
            domain=domain,
        )

    def withCookie( # NOSONAR
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
        self.setCookie(
            key,
            value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            http_only=http_only,
            same_site=same_site,
            partitioned=partitioned,
        )
        return self

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
        for key, options in cookies.items():
            if isinstance(options, Mapping):
                self.setCookie(key, **options)
            else:
                self.setCookie(key, options)
        return self

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
        self.deleteCookie(key, path=path, domain=domain)
        return self

    def withFlash(self, key: str, value: Any = None) -> Self:
        """
        Flash a status message into the session and return the response.

        The value survives for exactly one subsequent request and is read
        back in templates through the ``flash()`` global.

        Parameters
        ----------
        key : str
            Flash data key.
        value : Any, optional
            Value to flash.

        Returns
        -------
        Self
            The same response instance, allowing fluent chaining.
        """
        flash = self._flash
        if flash is None:
            flash = self._flash = {}

        flash[key] = value
        return self

    def withInput(self, values: Mapping[str, Any]) -> Self:
        """
        Flash the submitted payload so the next request can repopulate it.

        Values are read back in templates through the ``old()`` global.
        Credential-like fields such as ``password`` are stripped.

        Parameters
        ----------
        values : Mapping[str, Any]
            Submitted form payload to remember.

        Returns
        -------
        Self
            The same response instance, allowing fluent chaining.
        """
        flash = self._flash
        if flash is None:
            flash = self._flash = {}

        queue_bag(flash, OLD_INPUT_KEY, filter_input(values))
        return self

    def withErrors(self, errors: Mapping[str, Any] | Exception) -> Self:
        """
        Flash validation errors for the next request.

        Errors are read back in templates through the ``errors`` global.

        Parameters
        ----------
        errors : Mapping[str, Any] | Exception
            Mapping of field to message(s), or a validation exception.

        Returns
        -------
        Self
            The same response instance, allowing fluent chaining.
        """
        flash = self._flash
        if flash is None:
            flash = self._flash = {}

        queue_bag(flash, ERRORS_KEY, normalize_errors(errors))
        return self

    def getFlashData(self) -> dict[str, Any] | None:
        """
        Return the data queued by ``withFlash()`` for the session flash bag.

        Returns
        -------
        dict[str, Any] | None
            The queued key-value pairs, or None when nothing was queued.
        """
        return self._flash

    def getBody(self) -> bytes | None:
        """
        Return the response body as bytes.

        Returns
        -------
        bytes | None
            The response body as bytes, or None if not set.
        """
        return self._body

    def getStream(self) -> AsyncIterable[bytes] | None:
        """
        Return the response stream if present.

        Returns
        -------
        AsyncIterable[bytes] | None
            The response stream, or None if not set.
        """
        return self._stream

    def hasStream(self) -> bool:
        """
        Check if the response has a stream.

        Returns
        -------
        bool
            True if a stream is present, False otherwise.
        """
        return self._stream is not None

    async def runBackground(self) -> None:
        """
        Run the background task if it exists.

        Returns
        -------
        None
            This method does not return a value.
        """
        if self.background:
            await self.background()

    def getStatusCode(self) -> int:
        """
        Return the HTTP status code of the response.

        Returns
        -------
        int
            The HTTP status code.
        """
        return self.status_code

    def getMediaType(self) -> str | None:
        """
        Return the media type of the response.

        Returns
        -------
        str | None
            The media type, or None if not set.
        """
        return self.media_type

class HTMLResponse(Response):

    __slots__ = ()

    # Pre-computed constant avoids f-string evaluation on every instantiation
    _CONTENT_TYPE: ClassVar[str] = "text/html; charset=utf-8"

    def __init__(
        self,
        content: str | bytes = "",
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        """
        Initialize an HTMLResponse with HTML content.

        Parameters
        ----------
        content : str | bytes, optional
            HTML content to include in the response.
        status_code : HTTPStatus | int, optional
            HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Optional response headers.
        background : BackgroundTask | None, optional
            Optional background task to run after response.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/html",
            background=background,
        )

        if not self.hasHeader("content-type"):
            self.setHeader("content-type", self._CONTENT_TYPE)

class PlainTextResponse(Response):

    __slots__ = ()

    # Pre-computed constant avoids f-string evaluation on every instantiation
    _CONTENT_TYPE: ClassVar[str] = "text/plain; charset=utf-8"

    def __init__(
        self,
        content: str | bytes = "",
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        """
        Initialize a plain text response.

        Parameters
        ----------
        content : str | bytes, optional
            The plain text content for the response.
        status_code : HTTPStatus | int, optional
            The HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Optional response headers.
        background : BackgroundTask | None, optional
            Optional background task to run after response.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/plain",
            background=background,
        )

        if not self.hasHeader("content-type"):
            self.setHeader("content-type", self._CONTENT_TYPE)

class JSONResponse(Response):

    __slots__ = (
        "_json_default",
        "_json_ensure_ascii",
        "_json_indent",
        "_json_separators",
    )

    # Pre-computed constant avoids string allocation on every instantiation
    _CONTENT_TYPE: ClassVar[str] = "application/json; charset=utf-8"

    def __init__(
        self,
        content: Any,
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
        *,
        indent: int | None = None,
        ensure_ascii: bool = False,
        separators: tuple[str, str] | None = None,
        default: Any | None = None,
    ) -> None:
        """
        Initialize a JSONResponse with serialized JSON content.

        Parameters
        ----------
        content : Any
            Content to serialize as JSON.
        status_code : HTTPStatus | int, optional
            HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Response headers to include.
        background : BackgroundTask | None, optional
            Background task to run after response.
        indent : int | None, optional
            Indentation level for pretty-printing JSON.
        ensure_ascii : bool, optional
            Whether to escape non-ASCII characters.
        separators : tuple[str, str] | None, optional
            Item and key separators for JSON output.
        default : Any | None, optional
            Custom encoder for unsupported types.

        Returns
        -------
        None
            This constructor does not return a value.
        """
        # Store options before super().__init__ so render() can access them
        self._json_indent = indent
        self._json_ensure_ascii = ensure_ascii
        self._json_separators = separators
        # Reference the class function directly to avoid bound method allocation
        self._json_default = (
            default if default is not None else JSONResponse._defaultEncoder
        )

        # Initialize the parent Response with JSON media type
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="application/json",
            background=background,
        )

        # Ensure the Content-Type header is set for JSON responses
        if not self.hasHeader("content-type"):
            self.setHeader("content-type", self._CONTENT_TYPE)

    def render(self, content: Any) -> bytes:
        """
        Serialize content to JSON bytes.

        Parameters
        ----------
        content : Any
            The content to serialize as JSON.

        Returns
        -------
        bytes
            The serialized JSON content as UTF-8 encoded bytes.

        Raises
        ------
        TypeError
            If the content cannot be serialized to JSON.
        """
        # Cache slot descriptors as locals to minimize repeated attribute lookups
        indent = self._json_indent
        ensure_ascii = self._json_ensure_ascii
        separators = self._json_separators
        default_fn = self._json_default

        # Fast path via msgspec when no special formatting is needed
        if indent is None and not ensure_ascii and separators is None:
            try:
                return _msgspec_json.encode(content, enc_hook=default_fn)
            except TypeError as exc:
                error_msg = str(exc)
                raise TypeError(error_msg) from exc

        # Use compact separators when neither indent nor custom separators are set
        if separators is None and indent is None:
            separators = (",", ":")

        try:
            json_string = json.dumps(
                content,
                indent=indent,
                ensure_ascii=ensure_ascii,
                separators=separators,
                default=default_fn,
            )
        except TypeError as exc:
            error_msg = str(exc)
            raise TypeError(error_msg) from exc

        return json_string.encode("utf-8")

    @staticmethod
    def _defaultEncoder(obj: Any) -> Any:
        """
        Encode unsupported types for JSON serialization.

        Parameters
        ----------
        obj : Any
            The object to encode.

        Returns
        -------
        Any
            The encoded object suitable for JSON serialization.

        Raises
        ------
        TypeError
            If the object cannot be encoded for JSON serialization.
        """
        # Handle datetime, date, and time objects
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        # Handle Decimal objects
        if isinstance(obj, Decimal):
            return str(obj)
        # Handle UUID objects
        if isinstance(obj, UUID):
            return str(obj)
        # Handle Enum objects
        if isinstance(obj, Enum):
            return obj.value
        # Handle set and frozenset objects
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        # Raise error if object is not serializable
        error_msg = (
            f"Object of type {type(obj).__name__} is not JSON serializable"
        )
        raise TypeError(error_msg)

class RedirectResponse(Response):

    __slots__ = ()

    # Pre-computed constant avoids f-string evaluation on every instantiation
    _CONTENT_TYPE: ClassVar[str] = "text/plain; charset=utf-8"

    def __init__(
        self,
        url: str,
        status_code: HTTPStatus | int = 302,
        headers: Mapping[str, str] | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        """
        Initialize a redirect response.

        Parameters
        ----------
        url : str
            Target URL for redirection.
        status_code : HTTPStatus | int, optional
            Redirect status code (301, 302, 303, 307, 308).
        headers : Mapping[str, str] | None, optional
            Optional additional headers.
        background : BackgroundTask | None, optional
            Optional background task.

        Returns
        -------
        None
            This method does not return a value.
        """
        if not isinstance(url, str):
            error_msg = "url must be a string"
            raise TypeError(error_msg)

        if not 300 <= status_code <= 399:
            error_msg = "Redirect status_code must be 3xx"
            raise ValueError(error_msg)

        content = f"Redirecting to {url}"

        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/plain",
            background=background,
        )

        self.setHeader("location", url)

        if not self.hasHeader("content-type"):
            self.setHeader("content-type", self._CONTENT_TYPE)

class StreamingResponse(Response):

    __slots__ = ()

    def __init__(
        self,
        content: AsyncIterable[bytes] | Iterable[bytes],
        status_code: HTTPStatus | int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        """
        Initialize a streaming response.

        Parameters
        ----------
        content : AsyncIterable[bytes] | Iterable[bytes]
            Streaming content source.
        status_code : HTTPStatus | int, optional
            HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Optional response headers.
        media_type : str | None, optional
            Optional media type for the response.
        background : BackgroundTask | None, optional
            Optional background task to run after response.

        Returns
        -------
        None
            This constructor does not return a value.
        """
        if isinstance(content, AsyncIterable):
            stream = content
        elif isinstance(content, Iterable):
            stream = self._wrapSyncIterable(content)
        else:
            error_msg = (
                "StreamingResponse content must be "
                "AsyncIterable[bytes] or Iterable[bytes]"
            )
            raise TypeError(error_msg)

        super().__init__(
            content=stream,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

        self._body = None

        if media_type and not self.hasHeader("content-type"):
            self.setHeader(
                "content-type",
                f"{media_type}; charset={self.charset}"
                if media_type.startswith("text/")
                else media_type,
            )

    async def _wrapSyncIterable(
        self,
        iterable: Iterable[bytes],
    ) -> AsyncIterable[bytes]:
        """
        Adapt a synchronous iterable of bytes to an asynchronous iterable.

        Parameters
        ----------
        iterable : Iterable[bytes]
            The synchronous iterable yielding byte chunks.

        Returns
        -------
        AsyncIterable[bytes]
            An asynchronous iterable yielding byte chunks.

        Raises
        ------
        TypeError
            If any chunk in the iterable is not bytes-like.
        """
        for chunk in iterable:
            # Fast path: identity check avoids MRO traversal and skips copy
            if type(chunk) is bytes:
                yield chunk
            elif isinstance(chunk, (bytearray, memoryview)):
                yield bytes(chunk)
            else:
                error_msg = "StreamingResponse chunks must be bytes"
                raise TypeError(error_msg)

class FileResponse(StreamingResponse):

    __slots__ = ("_chunk_size", "_file_size", "_path")

    def __init__(
        self,
        path: str | Path,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        filename: str | None = None,
        chunk_size: int = 64 * 1024,
        background: BackgroundTask | None = None,
    ) -> None:
        """
        Initialize a file streaming response.

        Parameters
        ----------
        path : str | Path
            Path to the file to serve.
        status_code : int, default=200
            HTTP status code for the response.
        headers : Mapping[str, str] | None, optional
            Optional response headers.
        media_type : str | None, optional
            Optional media type for the response.
        filename : str | None, optional
            Optional filename for Content-Disposition header.
        chunk_size : int, default=65536
            Size of file chunks to read and send.
        background : BackgroundTask | None, optional
            Optional background task to run after response.

        Returns
        -------
        None
            This constructor does not return a value.
        """
        self._path = Path(path)

        if not self._path.exists():
            error_msg = f"File not found: {self._path}"
            raise FileNotFoundError(error_msg)

        if not self._path.is_file():
            error_msg = f"Path is not a file: {self._path}"
            raise ValueError(error_msg)

        self._chunk_size = chunk_size

        if media_type is None:
            guessed, _ = mimetypes.guess_type(str(self._path))
            media_type = guessed or "application/octet-stream"

        stream = self._fileIterator()

        super().__init__(
            content=stream,
            status_code=status_code,
            headers=headers,
            media_type=media_type,
            background=background,
        )

        # Compute and cache file size; avoids repeated stat() syscalls per request.
        self._file_size = self._path.stat().st_size
        self.setHeader("content-length", str(self._file_size))

        if filename:
            disposition = f'attachment; filename="{filename}"'
            self.setHeader("content-disposition", disposition)

    def getPath(self) -> Path:
        """
        Return the file path.

        Returns
        -------
        Path
            The path to the file being served.
        """
        return self._path

    def getFileSize(self) -> int:
        """
        Return the file size in bytes.

        Returns
        -------
        int
            The size of the file in bytes.
        """
        return self._file_size

    async def _fileIterator(self) -> AsyncIterable[bytes]:
        """
        Yield file content in chunks asynchronously.

        Returns
        -------
        AsyncIterable[bytes]
            An asynchronous iterable yielding file chunks as bytes.
        """
        # Cache method references to avoid per-iteration attribute lookups
        loop = asyncio.get_running_loop()
        executor = loop.run_in_executor
        chunk_size = self._chunk_size
        with self._path.open("rb") as file:
            read = file.read
            while True:
                chunk = await executor(None, read, chunk_size)
                if not chunk:
                    break
                yield chunk
