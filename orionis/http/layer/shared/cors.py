from __future__ import annotations
import re
from re import Pattern
from typing import TYPE_CHECKING, Final
from orionis.foundation.config.http.entitites.cors import Cors
from orionis.http.response import Response

if TYPE_CHECKING:
    from orionis.http.adapters.request.contracts.transport import TransportAdapter

class CORSException(Exception):
    ...

class CORSMiddleware:

    __slots__ = (
        "__allow_all_headers",
        "__allow_all_methods",
        "__allow_all_origins",
        "__allow_credentials",
        "__allow_headers_value",
        "__allow_methods_value",
        "__allow_origins",
        "__expose_headers_value",
        "__max_age_value",
        "__origin_regex",
    )

    # Methods allowed in CORS preflight responses when the wildcard is used.
    ALL_METHODS: Final[str] = (
        "DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
    )

    def __init__(
        self,
        config: dict,
    ) -> None:
        """Initialize the middleware with the given CORS configuration.

        Parameters
        ----------
        config : dict
            A dictionary whose keys must match ``Cors`` fields.

        Returns
        -------
        None
        """
        # Load cors configuration into a structured object for
        # easier access and validation.
        cors = Cors(**config)

        # Validate configuration
        if cors.allow_credentials and "*" in cors.allow_origins:
            msg = (
                "CORS configuration error: "
                "Cannot use wildcard origins with credentials enabled."
            )
            raise CORSException(msg)

        # Origins
        self.__allow_all_origins = "*" in cors.allow_origins
        self.__allow_origins = {
            origin.rstrip("/")
            for origin in cors.allow_origins
        }
        self.__origin_regex: Pattern[str] | None = (
            re.compile(cors.allow_origin_regex)
            if cors.allow_origin_regex
            else None
        )

        # Methods
        self.__allow_all_methods = "*" in cors.allow_methods
        self.__allow_methods_value = (
            self.ALL_METHODS
            if self.__allow_all_methods
            else ", ".join(
                method.upper()
                for method in cors.allow_methods
            )
        )

        # Headers
        self.__allow_all_headers = "*" in cors.allow_headers
        self.__allow_headers_value = (
            "*"
            if self.__allow_all_headers
            else ", ".join(
                header.lower()
                for header in cors.allow_headers
            )
        )
        self.__expose_headers_value = (
            ", ".join(
                header.lower()
                for header in cors.expose_headers
            )
            if cors.expose_headers
            else ""
        )

        # Credentials / Cache
        self.__allow_credentials = cors.allow_credentials

        # Pre-render the max-age header value; None disables the header.
        self.__max_age_value: str | None = (
            str(cors.max_age)
            if isinstance(cors.max_age, int)
            else None
        )

    def __isAllowedOrigin(
        self,
        origin: str,
    ) -> bool:
        """
        Validate whether an origin is allowed.

        Parameters
        ----------
        origin : str
            The ``Origin`` header value from the request.

        Returns
        -------
        bool
            ``True`` when the origin is permitted, ``False`` otherwise.
        """
        # Wildcard configuration accepts any origin without normalizing.
        if self.__allow_all_origins:
            return True

        normalized = origin.rstrip("/")

        if normalized in self.__allow_origins:
            return True

        return bool(
            self.__origin_regex
            and self.__origin_regex.match(normalized),
        )

    def __isPreflight(
        self,
        method: str,
        headers: object,
    ) -> bool:
        """
        Determine whether the request is a CORS preflight.

        Parameters
        ----------
        method : str
            The HTTP method of the incoming request.
        headers : object
            The parsed request headers (supports ``in`` operator).

        Returns
        -------
        bool
            ``True`` for preflight requests (OPTIONS + ACRM header).
        """
        # Transports already deliver uppercase verbs; normalise only on miss.
        if method != "OPTIONS" and method.upper() != "OPTIONS":
            return False
        return "access-control-request-method" in headers

    def __mergeVary(
        self,
        response: Response,
        value: str,
    ) -> None:
        """
        Append a directive to the ``Vary`` header without overwriting it.

        Parameters
        ----------
        response : Response
            The response object to modify.
        value : str
            The directive to add (e.g. ``"origin"``).

        Returns
        -------
        None
        """
        existing = response.getHeader("vary")
        if existing:
            # Avoid duplicates and preserve all pre-existing directives.
            directives = [
                d.strip().lower()
                for d in ", ".join(existing).split(",")
            ]
            if value.lower() not in directives:
                response.setHeader(
                    "vary",
                    ", ".join(existing) + f", {value}",
                )
        else:
            response.setHeader("vary", value)

    def __applyOrigin(
        self,
        response: Response,
        origin: str,
    ) -> None:
        """
        Write the ``Access-Control-Allow-Origin`` (and ``Vary``) headers.

        Parameters
        ----------
        response : Response
            The response object to modify.
        origin : str
            The ``Origin`` header value from the request.

        Returns
        -------
        None
        """
        if self.__allow_credentials:
            # Credentials require an explicit origin, never a wildcard.
            response.setHeader("access-control-allow-origin", origin)
            self.__mergeVary(response, "origin")
            return

        if self.__allow_all_origins:
            response.setHeader("access-control-allow-origin", "*")
            return

        # Reflect the specific origin and mark the response as varying.
        response.setHeader("access-control-allow-origin", origin)
        self.__mergeVary(response, "origin")

    def __applyCredentials(
        self,
        response: Response,
    ) -> None:
        """
        Write the ``Access-Control-Allow-Credentials`` header if needed.

        Parameters
        ----------
        response : Response
            The response object to modify.

        Returns
        -------
        None
        """
        if self.__allow_credentials:
            response.setHeader("access-control-allow-credentials", "true")

    def before(
        self,
        adapter: TransportAdapter,
    ) -> Response | None:
        """
        Intercept preflight requests and return an early response.

        Parameters
        ----------
        adapter : TransportAdapter
            Unified transport abstraction for the current request.

        Returns
        -------
        Response | None
            A 204 No Content preflight response, or ``None`` when the
            request is not a valid CORS preflight.
        """
        # Get the request headers from the adapter, which abstracts away the
        # underlying transport (ASGI, WSGI, etc.) and provides a consistent API
        headers = adapter.headers()

        # Get the Origin header, which is required for CORS requests. If it's not
        # present, this is not a CORS request and we can skip all CORS processing.
        origin = headers.get("origin")

        # Not a CORS request.
        if not origin:
            return None

        # Origin not allowed.
        if not self.__isAllowedOrigin(origin):
            return None

        # Not a preflight.
        if not self.__isPreflight(
            adapter.method() or "",
            headers,
        ):
            return None

        # Build preflight response
        response = Response(status_code=204)

        # Origin
        self.__applyOrigin(response, origin)

        # Methods
        response.setHeader(
            "access-control-allow-methods",
            self.__allow_methods_value,
        )

        # Headers.  With the wildcard configuration, reflect the headers
        # requested by the browser: the literal "*" is not honoured by
        # browsers when credentials are involved, so echoing the
        # Access-Control-Request-Headers value is the spec-safe choice.
        allow_headers_value = self.__allow_headers_value
        if self.__allow_all_headers:
            requested_headers = headers.get(
                "access-control-request-headers",
            )
            if requested_headers:
                allow_headers_value = requested_headers
                self.__mergeVary(
                    response,
                    "access-control-request-headers",
                )
        response.setHeader(
            "access-control-allow-headers",
            allow_headers_value,
        )

        # Credentials
        self.__applyCredentials(response)

        # Cache
        if self.__max_age_value is not None:
            response.setHeader(
                "access-control-max-age",
                self.__max_age_value,
            )

        # Return the preflight response immediately, without calling the app.
        return response

    def after(
        self,
        adapter: TransportAdapter,
        response: Response,
    ) -> Response:
        """
        Apply CORS headers to actual (non-preflight) responses.

        Parameters
        ----------
        adapter : TransportAdapter
            Unified transport abstraction for the current request.
        response : Response
            The response produced by the application.

        Returns
        -------
        Response
            The same response object, enriched with CORS headers.
        """
        # Get the request headers from the adapter, which abstracts away the
        # underlying transport (ASGI, WSGI, etc.) and provides a consistent API
        headers = adapter.headers()

        # Get the Origin header, which is required for CORS requests. If it's not
        # present, this is not a CORS request and we can skip all CORS processing.
        origin = headers.get("origin")

        # Not a CORS request.
        if not origin:
            return response

        # Origin not allowed.
        if not self.__isAllowedOrigin(origin):
            return response

        # Origin
        self.__applyOrigin(response, origin)

        # Credentials
        self.__applyCredentials(response)

        # Exposed headers
        if self.__expose_headers_value:
            response.setHeader(
                "access-control-expose-headers",
                self.__expose_headers_value,
            )

        # Return the modified response with CORS headers applied.
        return response
