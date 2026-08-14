from __future__ import annotations
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from orionis.http.contracts.request import IRequest
from orionis.http.enums.interfaces import Interface
from orionis.http.payload.estructures.cookies import Cookies
from orionis.http.payload.estructures.query_params import QueryParams
from orionis.http.payload.media_types import DEFAULT_MEDIA_TYPES, MediaTypeRegistry
from orionis.http.payload.parsers import (
    parse_content_type,
    parse_json,
    parse_msgpack,
    parse_urlencoded,
    parse_urlencoded_multi,
    parse_xml,
)
from orionis.http.payload.stream_parser import MultipartStreamParser

_MIME_JSON = "application/json"
_MIME_MULTIPART = "multipart/form-data"
_MIME_MSGPACK = "application/msgpack"
_MIME_URLENCODED = "application/x-www-form-urlencoded"
_BEARER_PREFIX = "Bearer "
_BEARER_PREFIX_LEN = 7

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from orionis.http.adapters.request.contracts.transport import TransportAdapter
    from orionis.http.payload.contracts.body_stream import IBodyStream
    from orionis.http.payload.estructures.headers import Headers
    from orionis.http.payload.form_data import FormData
    from xml.etree.ElementTree import Element as XMLElement

class UnsupportedMediaTypeException(Exception):
    """Raised when the request Content-Type is not supported by the parser."""

class Request(IRequest):

    __slots__ = (
        "__adapter",
        "__body_stream",
        "__cached_accept_lower",
        "__cached_base_url",
        "__cached_content_type",
        "__cached_cookies",
        "__cached_data",
        "__cached_form",
        "__cached_forwarded",
        "__cached_headers",
        "__cached_http_version",
        "__cached_ip",
        "__cached_json",
        "__cached_method",
        "__cached_multipart",
        "__cached_path",
        "__cached_port",
        "__cached_query_params",
        "__cached_scheme",
        "__cached_url",
        "__interface",
        "__json_parsed",
        "__path_params",
        "__registry",
        "__scope",
        "__state",
    )

    def __init__(
        self,
        interface: Interface,
        adapter: TransportAdapter,
        body_stream: IBodyStream,
        *,
        registry: MediaTypeRegistry | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize an HTTP request from an interface, adapter, and body stream.

        Parameters
        ----------
        interface : Interface
            Transport protocol type (ASGI or RSGI).
        adapter : TransportAdapter
            Provides the parsed scope dict and header accessor.
        body_stream : IBodyStream
            Pre-constructed body stream.  Inject a stub for unit testing.
        registry : MediaTypeRegistry | None, optional
            Content-type parser registry.  Defaults to ``DEFAULT_MEDIA_TYPES``.
        params : dict[str, Any] | None, optional
            Path parameters extracted from the URL. Defaults to None.

        Returns
        -------
        None
        """
        self.__scope = adapter.getScope()
        self.__adapter = adapter
        # Reuse the enum member directly when the caller already passes one.
        self.__interface = (
            interface
            if isinstance(interface, Interface)
            else Interface(interface)
        )
        self.__body_stream: IBodyStream = body_stream
        self.__registry: MediaTypeRegistry = (
            registry if registry is not None else DEFAULT_MEDIA_TYPES
        )
        self.__cached_url: str | None = None
        self.__cached_base_url = None
        self.__cached_headers = None
        self.__cached_query_params = None
        self.__cached_cookies = None
        self.__cached_ip = None
        self.__cached_port = None
        self.__cached_method = None
        self.__cached_scheme = None
        self.__cached_http_version = None
        self.__cached_data: dict[str, Any] | None = None
        self.__cached_json = None
        self.__json_parsed = False
        self.__cached_form = None
        self.__cached_multipart = None
        self.__cached_forwarded = None
        self.__cached_content_type = None
        self.__cached_path = None
        self.__cached_accept_lower = None
        self.__path_params: dict[str, Any] = params if params is not None else {}
        self.__state: SimpleNamespace = SimpleNamespace()

    def __buildUrlRSGI(self) -> str:
        """
        Build the full URL from an RSGI scope.

        Constructs the complete request URL by combining scheme, host, path,
        and query string from the RSGI scope.

        Returns
        -------
        str
            The constructed request URL.
        """
        scope = self.__scope

        scheme: str = scope["scheme"]
        path: str = scope["path"]
        query: str = scope["query_string"]

        # The Host header carries the origin the client actually used.
        host: str = self.headers.get("host") or scope["server"]

        if query:
            return f"{scheme}://{host}{path}?{query}"
        return f"{scheme}://{host}{path}"

    def __buildUrlASGI(self) -> str:
        """
        Build the full URL from an ASGI scope.

        Constructs the complete request URL by combining scheme, host, path,
        and query string from the ASGI scope.

        Returns
        -------
        str
            The constructed request URL.
        """
        scope = self.__scope

        # Populate the scheme and path caches while building the URL.
        scheme: str = self.scheme
        path: str = self.path
        query_bytes: bytes = scope.get("query_string", b"")
        query: str = (
            query_bytes.decode("latin-1") if query_bytes else ""
        )

        headers = self.headers

        host = headers.get("host")
        if host is None:
            server = scope.get("server")
            if server:
                host_name, port = server

                default_port = (
                    80 if scheme in ("http", "ws") else 443
                )

                host = (
                    host_name
                    if port == default_port
                    else f"{host_name}:{port}"
                )
            else:
                return f"{path}?{query}" if query else path

        if query:
            return f"{scheme}://{host}{path}?{query}"
        return f"{scheme}://{host}{path}"

    def __buildBaseUrlRSGI(self) -> str:
        """
        Build the base URL from an RSGI scope.

        Returns the base URL composed of scheme and host.

        Returns
        -------
        str
            The base URL (scheme://host).
        """
        scheme: str = self.__scope["scheme"]

        # The Host header carries the origin the client actually used.
        host: str = self.headers.get("host") or self.__scope["server"]

        return f"{scheme}://{host}"

    def __buildBaseUrlASGI(self) -> str:
        """
        Build the base URL from an ASGI scope.

        Constructs the base URL by combining scheme, host, and optional
        root_path from the ASGI scope.

        Returns
        -------
        str
            The base URL (scheme://host or scheme://host/root_path).
        """
        scope: dict[str, Any] = self.__scope

        # Populate the scheme cache while building the base URL.
        scheme: str = self.scheme
        headers = self.headers
        root_path: str = scope.get("root_path", "")

        host = headers.get("host")
        if host is None:
            server = scope.get("server")
            if server:
                host_name, port = server
                default_port = 80 if scheme == "http" else 443
                host = host_name if port == default_port else f"{host_name}:{port}"
            else:
                host = "localhost"

        # Include root_path if present
        if root_path:
            return f"{scheme}://{host}{root_path}"
        return f"{scheme}://{host}"

    def __contentType(self) -> tuple[str, dict[str, str]]:
        """
        Parse and cache the request Content-Type header.

        Returns
        -------
        tuple[str, dict[str, str]]
            Return the media type and parsed parameters from the
            ``Content-Type`` header.
        """
        # Cache parsed Content-Type data to avoid repeated parsing.
        if self.__cached_content_type is None:
            self.__cached_content_type = parse_content_type(
                self.headers.get("content-type", ""),
            )
        return self.__cached_content_type

    def __getAcceptLower(self) -> str:
        """
        Cache and return the lowercased request Accept header.

        Returns
        -------
        str
            Return the lowercased ``Accept`` header value, or an empty
            string when the header is missing.
        """
        # Cache normalized Accept value for repeated content negotiation checks.
        if self.__cached_accept_lower is None:
            self.__cached_accept_lower = self.headers.get("accept", "").lower()
        return self.__cached_accept_lower

    # ---- Private Data Parsers ----

    async def __parseDataJson(self) -> dict[str, Any]:
        """
        Parse JSON body for ``data()`` and populate the JSON cache.

        Returns
        -------
        dict[str, Any]
            Parsed JSON object from the request body.

        Raises
        ------
        ValueError
            If the JSON body is empty or cannot be decoded.
        TypeError
            If the decoded JSON payload is not an object.
        """
        # Reuse cached JSON when it has already been parsed.
        if self.__json_parsed:
            parsed = self.__cached_json
        else:
            raw = await self.__body_stream.read()
            if not raw:
                error_msg = "Empty JSON body"
                raise ValueError(error_msg)
            try:
                parsed = parse_json(raw)
                self.__cached_json = parsed
                self.__json_parsed = True
            except Exception as exc:
                error_msg = "Invalid JSON payload"
                raise ValueError(error_msg) from exc
        if not isinstance(parsed, dict):
            error_msg = "JSON body must be an object"
            raise TypeError(error_msg)
        return parsed  # type: ignore[return-value]

    async def __parseDataUrlencoded(self) -> dict[str, Any]:
        """
        Parse URL-encoded body for ``data()`` with multi-value support.

        Returns
        -------
        dict[str, Any]
            Parsed form mapping where repeated keys are preserved as lists.
        """
        # Parse raw bytes directly into a multi-value dictionary.
        raw = await self.__body_stream.read()
        return parse_urlencoded_multi(raw)

    async def __parseDataMultipart(self) -> dict[str, Any]:
        """
        Parse multipart body for ``data()`` in a single pass.

        Returns
        -------
        dict[str, Any]
            Merged mapping of multipart fields and uploaded files.
        """
        # Collapse repeated keys into lists while preserving first-value fast path.
        form = await self.form()
        merged: dict[str, Any] = {}
        for k, v in form.allItems:
            existing = merged.get(k)
            if existing is None:
                merged[k] = v
            elif isinstance(existing, list):
                existing.append(v)
            else:
                merged[k] = [existing, v]
        return merged

    async def __parseDataMsgpack(self) -> dict[str, Any]:
        """
        Parse MessagePack body for ``data()``.

        Returns
        -------
        dict[str, Any]
            Decoded MessagePack mapping.

        Raises
        ------
        ValueError
            If the MessagePack payload cannot be decoded.
        TypeError
            If the decoded MessagePack payload is not a map.
        """
        # Decode MessagePack payload and validate expected mapping shape.
        raw = await self.__body_stream.read()
        try:
            parsed = parse_msgpack(raw)
        except Exception as exc:
            error_msg = "Invalid MessagePack payload"
            raise ValueError(error_msg) from exc
        if not isinstance(parsed, dict):
            error_msg = "MessagePack body must be a map"
            raise TypeError(error_msg)
        return parsed  # type: ignore[return-value]

    # ---- Properties: Request Line ----

    @property
    def method(self) -> str:
        """
        Return the HTTP request method.

        Returns
        -------
        str
            The HTTP method of the request, such as 'GET' or 'POST'.
        """
        if self.__cached_method is not None:
            return self.__cached_method

        self.__cached_method = self.__scope["method"]
        return self.__cached_method

    @property
    def scheme(self) -> str:
        """
        Return the URL scheme (e.g., 'http' or 'https') of the request.

        Returns
        -------
        str
            The URL scheme of the request.
        """
        if self.__cached_scheme is not None:
            return self.__cached_scheme

        self.__cached_scheme = self.__scope.get("scheme", "http")
        return self.__cached_scheme

    @property
    def path(self) -> str:
        """
        Return the request path.

        Returns
        -------
        str
            The path component of the request URL.
        """
        if self.__cached_path is None:
            self.__cached_path = self.__scope.get("path", "/")
        return self.__cached_path

    @property
    def httpVersion(self) -> str:
        """
        Return the HTTP version of the request.

        Returns
        -------
        str
            The HTTP version string, such as '1.1' or '2'.
        """
        if self.__cached_http_version is not None:
            return self.__cached_http_version

        self.__cached_http_version = self.__scope.get("http_version", "1.1")
        return self.__cached_http_version

    @property
    def interface(self) -> Interface:
        """
        Return the interface type of the request (ASGI or RSGI).

        Returns
        -------
        Interface
            The interface type of the request.
        """
        return self.__interface

    # ---- Properties: URL ----

    @property
    def url(self) -> str:
        """
        Return the full request URL.

        Returns
        -------
        str
            Absolute URL including scheme, host, path, and query string.
            Result is cached after the first call.
        """
        if self.__cached_url is None:
            self.__cached_url = (
                self.__buildUrlRSGI()
                if self.__interface is Interface.RSGI
                else self.__buildUrlASGI()
            )
        return self.__cached_url

    @property
    def baseUrl(self) -> str:
        """
        Return the base URL (scheme and host) for the request.

        Returns
        -------
        str
            Base URL composed of scheme, host, and optional root_path.
            Result is cached after the first call.
        """
        # Use cached base URL if available; build and cache on first access.
        if self.__cached_base_url is None:
            self.__cached_base_url = (
                self.__buildBaseUrlRSGI()
                if self.__interface is Interface.RSGI
                else self.__buildBaseUrlASGI()
            )
        return self.__cached_base_url

    # ---- Properties: Headers & Structures ----

    @property
    def headers(self) -> Headers:
        """
        Return the request headers as a Headers object.

        Returns
        -------
        Headers
            The headers associated with the request.
        """
        if self.__cached_headers is None:
            self.__cached_headers = self.__adapter.headers()
        return self.__cached_headers

    @property
    def queryParams(self) -> QueryParams:
        """
        Return parsed query parameters from the request URL.

        Returns
        -------
        QueryParams
            Parsed query parameters.  Result is cached after the first call.
        """
        if self.__cached_query_params is not None:
            return self.__cached_query_params

        scope: Any = self.__scope

        # Determine query string based on interface type
        if self.__interface is Interface.RSGI:
            query_string: str = scope["query_string"] or ""
        else:
            raw_qs: bytes = scope.get("query_string", b"")
            query_string = raw_qs.decode("latin-1")

        self.__cached_query_params = QueryParams(query_string)
        return self.__cached_query_params

    @property
    def cookies(self) -> Cookies:
        """
        Return parsed cookies from the request.

        Returns
        -------
        Cookies
            The parsed cookies as a Cookies object.
        """
        if self.__cached_cookies is not None:
            return self.__cached_cookies

        cookie_header: str | None = self.headers.get("cookie")
        self.__cached_cookies = Cookies(cookie_header)
        return self.__cached_cookies

    # ---- Properties: Client Info ----

    @property
    def ip(self) -> str | None:
        """
        Return the client's IP address from the request scope.

        After the ProxiesMiddleware runs, the adapter always stores the
        normalized plain-string IP in the scope via setState. For ASGI
        without proxy middleware, the original (host, port) tuple is handled
        as a fallback.

        Returns
        -------
        str | None
            The client's IP address if available, otherwise None.
        """
        if self.__cached_ip is not None:
            return self.__cached_ip

        raw = self.__scope.get("client")
        if raw is None:
            return None

        # Fallback for ASGI (host, port) tuple when adapter.client() was not called
        if isinstance(raw, (list, tuple)):
            self.__cached_ip = str(raw[0])
        else:
            self.__cached_ip = str(raw)

        return self.__cached_ip

    @property
    def port(self) -> int | None:
        """
        Return the client's port number from the request scope.

        Returns
        -------
        int | None
            The client's port number if available, otherwise None.
        """
        if self.__cached_port is not None:
            return self.__cached_port

        self.__cached_port = self.__scope.get("port")
        return self.__cached_port

    @property
    def forwarded(self) -> dict[str, Any]:
        """
        Return the forwarded information from the request scope.

        Returns
        -------
        dict[str, Any]
            The forwarded information as a dictionary.
        """
        if self.__cached_forwarded is not None:
            return self.__cached_forwarded
        self.__cached_forwarded = self.__scope.get("forwarded", {})
        return self.__cached_forwarded

    # ---- Properties: User Agent & Authentication ----

    @property
    def userAgent(self) -> str | None:
        """
        Return the User-Agent string from the request headers.

        Returns
        -------
        str | None
            The User-Agent string if present, otherwise None.
        """
        return self.headers.get("user-agent")

    @property
    def authorization(self) -> str | None:
        """
        Return the Authorization header value if present.

        Returns
        -------
        str | None
            The value of the 'Authorization' header, or None if not present.
        """
        return self.headers.get("authorization")

    @property
    def bearerToken(self) -> str | None:
        """
        Return the bearer token from the Authorization header if present.

        Returns
        -------
        str | None
            The bearer token extracted from the 'Authorization' header,
            or None if not present or does not start with 'Bearer '.
        """
        auth_header: str | None = self.headers.get("authorization")
        if auth_header and auth_header.startswith(_BEARER_PREFIX):
            return auth_header[_BEARER_PREFIX_LEN:]
        return None

    @property
    def apiKey(self) -> str | None:
        """
        Return the API key from the request headers if present.

        Returns
        -------
        str | None
            The API key from the 'X-API-Key' header, or None if not present.
        """
        return self.headers.get("x-api-key")

    # ---- Properties: Content Negotiation ----

    @property
    def accept(self) -> str | None:
        """
        Return the value of the Accept header.

        Returns
        -------
        str | None
            The value of the 'Accept' header, or None if not present.
        """
        return self.headers.get("accept")

    # ---- Properties: State & Scope ----

    @property
    def state(self) -> SimpleNamespace:
        """
        Return the mutable request state namespace.

        Middleware and handlers can attach arbitrary attributes to this
        namespace without polluting the scope dict.  Modelled after
        Starlette's ``request.state``.

        Returns
        -------
        types.SimpleNamespace
            The mutable state object for this request.
        """
        return self.__state

    @property
    def scope(self) -> dict[str, Any]:
        """
        Return the raw ASGI / RSGI connection scope.

        Exposes the underlying scope dict so that ASGI-aware middleware,
        tracing libraries, and extensions can read or annotate transport-level
        data without requiring framework-specific adapters.

        Returns
        -------
        dict[str, Any]
            The raw scope dictionary provided by the transport layer.
        """
        return self.__scope

    # ---- Body Reading Methods ----

    async def stream(self) -> AsyncGenerator[bytes]:
        """
        Yield chunks of the request body as they arrive.

        Delegates to ``BodyStream``, which handles RSGI and ASGI transports,
        enforces ``max_body_size``, and replays from the internal buffer when
        the body has already been fully read by ``body()`` or a parser.

        Returns
        -------
        AsyncGenerator[bytes]
            Yields chunks of the request body as bytes.
        """
        async for chunk in self.__body_stream.stream():
            yield chunk

    async def body(self) -> bytes:
        """
        Return the full request body as bytes.

        Buffers the stream on first call and caches the result.
        Subsequent calls are O(1) — they return the cached buffer.

        Returns
        -------
        bytes
            The complete request body as bytes.
        """
        return await self.__body_stream.read()

    async def raw(self) -> bytes:
        """
        Return the request body as raw bytes.

        Returns
        -------
        bytes
            The raw request body.
        """
        return await self.__body_stream.read()

    async def text(self) -> str:
        """
        Decode the request body as UTF-8 text.

        Returns
        -------
        str
            The decoded request body.
        """
        raw = await self.__body_stream.read()
        return raw.decode("utf-8")

    # ---- Structured Parsing Methods ----

    async def json(self) -> object:
        """
        Parse the request body as JSON.

        Validates ``Content-Type``, buffers the body, and delegates
        decoding to ``msgspec``.  Result is cached; a JSON ``null``
        literal is handled correctly via the ``__json_parsed`` sentinel.

        Returns
        -------
        dict[str, Any]
            The parsed JSON object.

        Raises
        ------
        UnsupportedMediaTypeException
            If the Content-Type is not ``application/json`` (or a
            ``+json`` subtype).
        ValueError
            If the body is empty or not valid JSON.
        """
        if self.__json_parsed:
            return self.__cached_json

        media_type, _ = self.__contentType()

        if media_type != _MIME_JSON and not media_type.endswith("+json"):
            error_msg = "Content-Type must be application/json"
            raise UnsupportedMediaTypeException(error_msg)

        raw = await self.__body_stream.read()

        if not raw:
            error_msg = "Empty JSON body"
            raise ValueError(error_msg)

        try:
            self.__cached_json = parse_json(raw)
            self.__json_parsed = True
        except Exception as exc:
            error_msg = "Invalid JSON payload"
            raise ValueError(error_msg) from exc

        return self.__cached_json

    async def xml(self) -> XMLElement:
        """
        Parse the request body as XML.

        Uses ``defusedxml`` to guard against XML bomb, XXE, entity
        expansion, and DTD-based attacks.

        Returns
        -------
        XMLElement (xml.etree.ElementTree.Element)
            Root element of the parsed XML document.

        Raises
        ------
        xml.etree.ElementTree.ParseError
            If the payload is malformed or contains forbidden constructs.
        """
        raw = await self.__body_stream.read()
        return parse_xml(raw)

    async def msgpack(self) -> dict[str, Any]:
        """
        Decode the request body as MessagePack.

        Returns
        -------
        dict[str, Any]
            The decoded Python object.

        Raises
        ------
        msgspec.DecodeError
            If the payload is not valid MessagePack.
        """
        raw = await self.__body_stream.read()
        return parse_msgpack(raw)

    async def formUrlEncoded(self) -> dict[str, Any]:
        """
        Parse ``application/x-www-form-urlencoded`` body.

        Returns
        -------
        dict[str, Any]
            Parsed form fields. Result is cached.

        Raises
        ------
        UnsupportedMediaTypeException
            If the Content-Type is not ``application/x-www-form-urlencoded``.
        """
        if self.__cached_form is not None:
            return self.__cached_form

        media_type, _ = self.__contentType()
        if media_type != _MIME_URLENCODED:
            error_msg = "Content-Type must be application/x-www-form-urlencoded"
            raise UnsupportedMediaTypeException(error_msg)

        raw = await self.__body_stream.read()
        self.__cached_form = parse_urlencoded(raw)
        return self.__cached_form

    async def form(self) -> FormData:
        """
        Parse ``multipart/form-data`` using a streaming parser.

        The boundary is extracted with a proper RFC 2046-compatible
        parser, so quoted boundaries and extra parameters are handled
        correctly.  The ``BodyStream`` provides transparent replay:
        if ``body()`` was called first, the buffer is streamed to the
        multipart parser instead of re-reading the transport.

        Returns
        -------
        FormData
            Parsed multipart form data. Result is cached.

        Raises
        ------
        UnsupportedMediaTypeException
            If the Content-Type is not ``multipart/form-data``.
        ValueError
            If the multipart boundary is absent.
        """
        if self.__cached_multipart is not None:
            return self.__cached_multipart

        media_type, params = self.__contentType()

        if media_type != _MIME_MULTIPART:
            error_msg = "Not multipart/form-data"
            raise UnsupportedMediaTypeException(error_msg)

        boundary_str = params.get("boundary", "")
        if not boundary_str:
            error_msg = "Missing multipart boundary"
            raise ValueError(error_msg)

        parser = MultipartStreamParser(
            self.__body_stream.stream(),
            boundary_str.encode(),
        )

        self.__cached_multipart = await parser.parse()
        return self.__cached_multipart

    async def payload(self) -> object:
        """
        Parse and return structured data according to ``Content-Type``.

        Dispatches to the registered ``BodyParser`` callable from
        ``MediaTypeRegistry``.  ``multipart/form-data`` is handled
        separately because it requires a streaming body, not a pre-buffered
        ``bytes`` value.  Falls back to raw bytes when the media type is
        absent or not registered.

        Returns
        -------
        object
            Parsed body, or raw ``bytes`` when no parser matches.
        """
        # Resolve media type from the cached Content-Type header.
        media_type, _ = self.__contentType()
        if not media_type:
            return await self.__body_stream.read()

        # Multipart needs the live stream — delegate to the dedicated method.
        if media_type == _MIME_MULTIPART:
            return await self.form()

        parser = self.__registry.get(media_type)
        if parser is None:
            return await self.__body_stream.read()

        return parser(await self.__body_stream.read())

    async def data(self) -> dict[str, Any]:
        """
        Return a flat dictionary parsed from the request body.

        Cache the parsed value so repeated calls are O(1).

        Parsing is selected by ``Content-Type``:

        - ``application/json`` -> JSON object (must be a mapping)
        - ``application/x-www-form-urlencoded`` -> form fields with
            scalar-or-list collapsing for repeated keys
        - ``multipart/form-data`` -> text fields and uploaded files with the
            same scalar-or-list collapsing
        - ``application/msgpack`` -> MessagePack object (must be a mapping)

        Returns
        -------
        dict[str, Any]
            Flat dictionary suitable for downstream request validation.

        Raises
        ------
        UnsupportedMediaTypeException
            Raise if ``Content-Type`` cannot be converted to a dictionary.
        ValueError
            Raise if JSON or MessagePack content is not a mapping.
        """
        # Return the cached body dictionary if already parsed.
        if self.__cached_data is not None:
            return self.__cached_data

        # Resolve media type from the cached Content-Type header.
        media_type, _ = self.__contentType()

        # Dispatch to the appropriate body parser based on media type.
        if media_type == _MIME_JSON:
            self.__cached_data = await self.__parseDataJson()
        elif media_type == _MIME_URLENCODED:
            self.__cached_data = await self.__parseDataUrlencoded()
        elif media_type == _MIME_MULTIPART:
            self.__cached_data = await self.__parseDataMultipart()
        elif media_type == _MIME_MSGPACK:
            self.__cached_data = await self.__parseDataMsgpack()
        else:
            ct = media_type or "unknown"
            error_msg = f"Cannot convert Content-Type '{ct}' to a dictionary"
            raise UnsupportedMediaTypeException(error_msg)

        return self.__cached_data

    # ---- Content Negotiation Methods ----

    def wantsJson(self) -> bool:
        """
        Determine if the client prefers a JSON response based on the Accept header.

        Returns
        -------
        bool
            True if the Accept header contains ``application/json`` or any
            ``+json`` subtype.
        """
        accept = self.__getAcceptLower()
        return _MIME_JSON in accept or "+json" in accept

    def wantsHtml(self) -> bool:
        """
        Determine if the client expects an HTML response based on the Accept header.

        Returns
        -------
        bool
            True if the Accept header indicates HTML is expected.
        """
        accept = self.__getAcceptLower()
        return "text/html" in accept or "*/*" in accept

    def wantsXml(self) -> bool:
        """
        Determine if the client prefers an XML response based on the Accept header.

        Returns
        -------
        bool
            True if the Accept header indicates XML is preferred.
        """
        accept = self.__getAcceptLower()
        return "application/xml" in accept or "text/xml" in accept

    def accepts(self, mime: str) -> bool:
        """
        Check if the client accepts a specific MIME type.

        Parameters
        ----------
        mime : str
            The MIME type to check.

        Returns
        -------
        bool
            True if the MIME type is present in the Accept header.
        """
        accept = self.__getAcceptLower()
        return mime.lower() in accept

    def isAjax(self) -> bool:
        """
        Determine if the request was made via AJAX.

        Returns
        -------
        bool
            True if the X-Requested-With header is 'XMLHttpRequest'.
        """
        return self.headers.get("x-requested-with") == "XMLHttpRequest"

    # ---- Route Parameter Methods ----

    def routeParam(self, key: str) -> dict[str, Any] | str | None:
        """
        Return a specific path parameter by key.

        Parameters
        ----------
        key : str
            The specific path parameter key to retrieve.

        Returns
        -------
        dict[str, Any] | str | None
            The specific parameter value if key exists, or None if key is not found.
            if key exists, or None if key is not found.
        """
        return self.__path_params.get(key)

    def routeParams(self) -> dict[str, Any]:
        """
        Return all path parameters as a dictionary.

        Returns
        -------
        dict[str, Any]
            A dictionary of all path parameters.
        """
        return self.__path_params

    # ---- CSRF Helpers ----

    def csrfToken(self) -> str | None:
        """
        Return the CSRF token for the current request.

        The token is set on ``request.state.csrf_token`` by
        ``CSRFTokenMiddleware`` before the route handler is called.
        Returns ``None`` when the middleware has not run (e.g. API routes).

        Returns
        -------
        str | None
            The CSRF token, or ``None`` when not available.
        """
        return getattr(self.__state, "csrf_token", None)

    @property
    def csrf_token(self) -> str | None:
        """
        CSRF token for the current request.

        Convenience property that delegates to ``csrfToken()``.  Intended
        for use in template engines:

        .. code-block:: html

            <input type="hidden" name="_csrf" value="{{ request.csrf_token }}">

        Returns
        -------
        str | None
            The CSRF token, or ``None`` when not available.
        """
        return getattr(self.__state, "csrf_token", None)
