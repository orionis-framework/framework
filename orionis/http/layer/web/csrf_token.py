from __future__ import annotations
import secrets
from typing import TYPE_CHECKING
from orionis.foundation.config.http.entitites.csrf import HTTPCsrf
from orionis.http.layer.web.exceptions import CSRFTokenMismatchException
from orionis.http.middleware import BaseMiddleware

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from orionis.http.request import Request
    from orionis.http.responses import Response

# ---------------------------------------------------------------------------
# Module-level constants — allocated once, never per-request.
# ---------------------------------------------------------------------------

# HTTP methods that do not mutate state: CSRF check is skipped entirely.
_SAFE_METHODS: frozenset[str] = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Content-Types that may carry the CSRF value inside the request body.
_FORM_MIME_URLENCODED: str = "application/x-www-form-urlencoded"
_FORM_MIME_MULTIPART: str = "multipart/form-data"

# Request header names inspected for the submitted value (lowercase).
_HDR_CSRF: str = "x-csrf-token"
_HDR_XSRF: str = "x-xsrf-token"

# Form field names inspected for the submitted value, in priority order.
_FIELD_CSRF: str = "_csrf"
_FIELD_CSRF_ALT: str = "csrf_token"


class CSRFTokenMiddleware(BaseMiddleware):
    """
    Web-layer middleware that enforces Cross-Site Request Forgery protection.

    Design decisions
    ----------------
    * **Session-bound token** — a single token is generated per session and
      reused for its entire lifetime.  Regeneration happens only on
      privilege changes (login / logout) which must call
      ``session.regenerate()`` explicitly; the middleware detects the fresh
      session and issues a new token automatically.
    * **Cryptographic token** — ``secrets.token_urlsafe(n)`` produces
      URL-safe Base-64 output from the OS CSPRNG.  32 bytes → 256 bits of
      entropy, well above the OWASP minimum.
    * **Timing-safe comparison** — ``secrets.compare_digest()`` is used
      exclusively; plain ``==`` is never used.
    * **Header-first extraction** — ``X-CSRF-Token`` and ``X-XSRF-Token``
      are checked before touching the body.  Body parsing is skipped
      entirely when the token is already present in a header, avoiding
      unnecessary I/O on API-style clients.
    * **XSRF-TOKEN cookie** — opt-in double-submit cookie pattern for
      Angular, Axios, and other JavaScript frameworks.  The cookie is
      intentionally *not* ``HttpOnly`` so client scripts can read it.
    * **Immediate exit paths** — the hot path bails out as early as
      possible for safe methods and disabled middleware, adding near-zero
      overhead for the common GET case.  Route-level exclusions are
      handled by the router (don't add the middleware to those routes).
    * **No global state** — all request-scoped data flows through
      ``request.state``; the middleware instance itself is stateless.
    """

    __slots__ = (
        "_cfg",
        "_enabled",
        "_session_key",
        "_token_length",
        "_xsrf_cookie",
    )

    def __init__(self, config: dict) -> None:
        """
        Initialise the middleware from a raw configuration dictionary.

        Parameters
        ----------
        config : dict
            Key-value pairs that correspond to ``HTTPCsrf`` fields.
            An empty dict uses all framework defaults.

        Returns
        -------
        None
        """
        cfg = HTTPCsrf(**config)
        self._cfg: HTTPCsrf = cfg

        # Cache hot-path flags at construction time to skip attribute
        # look-ups on every request.
        self._enabled: bool = cfg.enabled
        self._session_key: str = cfg.session_key
        self._token_length: int = cfg.token_length
        self._xsrf_cookie: bool = cfg.xsrf_cookie

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def handle(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
        """
        Execute the CSRF lifecycle for one HTTP request.

        For *safe* methods the token is attached to ``request.state``
        so templates can render the hidden field, and the request
        proceeds without any token comparison.

        For *unsafe* methods the submitted token is extracted, compared
        against the session token, and ``CSRFTokenMismatchException`` is
        raised on mismatch before the handler is ever called.

        Parameters
        ----------
        request : Request
            Incoming HTTP request with an active session available at
            ``request.state.session``.
        call_next : Callable[[], Awaitable[Response]]
            No-arg async callable that advances through the rest of the
            middleware pipeline and into the route handler.

        Returns
        -------
        Response
            HTTP response, optionally augmented with the ``XSRF-TOKEN``
            cookie when ``xsrf_cookie`` is enabled.

        Raises
        ------
        CSRFTokenMismatchException
            When an unsafe request does not supply a valid CSRF token.
        """
        # ── Fast exit: middleware is administratively disabled ──────────
        if not self._enabled:
            return await call_next()

        method: str = request.method

        # ── Fast exit: safe methods never mutate state ──────────────────
        if method in _SAFE_METHODS:
            return await self.__handleSafe(request, call_next)

        # ── Resolve or generate the session token ───────────────────────
        token = self.__resolveToken(request)

        # Expose on request.state for template engines.
        request.state.csrf_token = token

        # ── Extract submitted value (header-first for performance) ──────
        submitted: str | None = self.__extractFromHeaders(request)
        if submitted is None:
            submitted = await self.__extractFromBody(request)

        # ── Timing-safe comparison ───────────────────────────────────────
        valid = submitted is not None and secrets.compare_digest(
            token.encode(),
            submitted.encode(),
        )
        if not valid:
            error_msg = (
                "CSRF token mismatch: the supplied token does not match "
                "the one stored in the current session."
            )
            raise CSRFTokenMismatchException(error_msg)

        response = await call_next()

        # ── Optionally refresh the XSRF cookie ──────────────────────────
        if self._xsrf_cookie:
            self.__attachXsrfCookie(request, response, token)

        return response

    async def __handleSafe(
        self,
        request: Request,
        call_next: Callable[[], Awaitable[Response]],
    ) -> Response:
        """
        Process a safe HTTP method: attach the token and pass through.

        Parameters
        ----------
        request : Request
            Incoming safe-method request.
        call_next : Callable[[], Awaitable[Response]]
            Pipeline continuation.

        Returns
        -------
        Response
            Downstream response, optionally with the XSRF cookie set.
        """
        token = self.__resolveToken(request)
        request.state.csrf_token = token
        response = await call_next()
        if self._xsrf_cookie:
            self.__attachXsrfCookie(request, response, token)
        return response

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def __resolveToken(self, request: Request) -> str:
        """
        Return the CSRF token for this session, creating it if absent.

        A new token is generated when:

        * the session has no token yet (first request for this session), or
        * the session was just regenerated (login / logout / privilege change).

        The token is never regenerated on a per-request basis — this would
        invalidate tokens in parallel tab scenarios.

        Parameters
        ----------
        request : Request
            Current request; session is read from ``request.state.session``.

        Returns
        -------
        str
            URL-safe Base-64 CSRF token.
        """
        session = getattr(request.state, "session", None)
        if session is None:
            # Defensive path: session middleware did not run.
            # Return a per-request ephemeral token — it cannot be validated
            # across requests, but at least it does not expose a static value.
            return secrets.token_urlsafe(self._token_length)

        existing: str | None = session.get(self._session_key)
        if existing:
            return existing

        # Generate a cryptographically secure token.
        # token_urlsafe(32) → 43 characters of Base-64, 256 bits of entropy.
        token = secrets.token_urlsafe(self._token_length)
        session.put(self._session_key, token)
        return token

    # ------------------------------------------------------------------
    # Token extraction
    # ------------------------------------------------------------------

    @staticmethod
    def __extractFromHeaders(request: Request) -> str | None:
        """
        Return the CSRF token from the request headers, or ``None``.

        Checks ``X-CSRF-Token`` first, then ``X-XSRF-Token``.  Header
        inspection is O(1) and involves no I/O, so it is always tried
        before the request body.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.

        Returns
        -------
        str | None
            Token string if found, otherwise ``None``.
        """
        headers = request.headers

        value = headers.get(_HDR_CSRF)
        if value:
            return value.strip() or None

        value = headers.get(_HDR_XSRF)
        if value:
            return value.strip() or None

        return None

    @staticmethod
    async def __extractFromBody(request: Request) -> str | None:
        """
        Return the CSRF token from the parsed form body, or ``None``.

        Only invoked for ``application/x-www-form-urlencoded`` and
        ``multipart/form-data`` requests; JSON and other content-types
        are expected to supply the token via a header.  Body parsing is
        deliberately deferred to this point: when the token is already
        in a header this method is never called.

        Checked field names (in order): ``_csrf``, ``csrf_token``.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.

        Returns
        -------
        str | None
            Token string if found, otherwise ``None``.
        """
        content_type: str = request.headers.get("content-type", "")

        # Skip body parsing for non-form content types.
        if (
            _FORM_MIME_URLENCODED not in content_type
            and _FORM_MIME_MULTIPART not in content_type
        ):
            return None

        try:
            body: dict = await request.data()
        except Exception:  # noqa: BLE001
            # Malformed body: treat as missing token — let comparison fail.
            return None

        value = body.get(_FIELD_CSRF)
        if isinstance(value, str) and value:
            return value

        value = body.get(_FIELD_CSRF_ALT)
        if isinstance(value, str) and value:
            return value

        return None

    # ------------------------------------------------------------------
    # XSRF cookie
    # ------------------------------------------------------------------

    def __attachXsrfCookie(
        self,
        request: Request,
        response: Response,
        token: str,
    ) -> None:
        """
        Set the ``XSRF-TOKEN`` cookie on the outgoing response.

        The cookie is intentionally **not** ``HttpOnly`` so that
        JavaScript frameworks (Angular, Axios) can read it and forward
        it as the ``X-XSRF-Token`` request header.

        The ``Secure`` flag is promoted to ``True`` automatically when
        the current request arrives over HTTPS, regardless of the
        ``cookie_secure`` configuration value.

        Parameters
        ----------
        request : Request
            Provides the scheme to decide whether to promote the Secure flag.
        response : Response
            Response to which the ``Set-Cookie`` header is appended.
        token : str
            CSRF token to embed in the cookie value.

        Returns
        -------
        None
        """
        cfg = self._cfg
        secure = cfg.cookie_secure or request.scheme == "https"

        response.setCookie(
            key=cfg.cookie_name,
            value=token,
            path=cfg.cookie_path,
            domain=cfg.cookie_domain,
            secure=secure,
            http_only=False,  # Must be readable by JavaScript.
            same_site=cfg.cookie_same_site,
        )
