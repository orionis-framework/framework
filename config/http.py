from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.http import (
    HTTP, Cors, HTTPBodyLimits, HTTPCsrf, HTTPProxies, HTTPRateLimit, HTTPSecurity,
    HTTPWebSocket,
)

@dataclass(frozen=True, kw_only=True)
class BootstrapHTTP(HTTP):

    # ----------------------------------------------------------------------------------
    # body_limits : HTTPBodyLimits | dict, optional
    # --- Finite per-request budgets and immediate overload rejection per worker.
    # ----------------------------------------------------------------------------------
    body_limits: HTTPBodyLimits | dict = field(
        default_factory=lambda: HTTPBodyLimits(
            max_body_size=Env.get("HTTP_MAX_BODY_SIZE", 16 * 1024 * 1024),
            max_buffer_size=Env.get("HTTP_MAX_BUFFER_SIZE", 2 * 1024 * 1024),
            max_concurrent_requests=Env.get("HTTP_MAX_CONCURRENT_REQUESTS", 128),
            max_files=Env.get("HTTP_MAX_FILES", 32),
            max_fields=Env.get("HTTP_MAX_FIELDS", 128),
            max_part_size=Env.get("HTTP_MAX_PART_SIZE", 10 * 1024 * 1024),
            max_field_size=Env.get("HTTP_MAX_FIELD_SIZE", 1024 * 1024),
            max_header_size=Env.get("HTTP_MAX_PART_HEADER_SIZE", 16 * 1024),
            memory_threshold=Env.get("HTTP_UPLOAD_MEMORY_THRESHOLD", 256 * 1024),
            max_memory_size=Env.get("HTTP_MAX_MULTIPART_MEMORY_SIZE", 8 * 1024 * 1024),
        ),
    )

    # ----------------------------------------------------------------------------------
    # monitor_disconnects : bool, optional
    # --- Enable request cancellation when the client disconnects.
    # ----------------------------------------------------------------------------------
    monitor_disconnects: bool = field(
        default_factory=lambda: Env.get("HTTP_MONITOR_DISCONNECTS", False),
    )

    # ----------------------------------------------------------------------------------
    # websocket : HTTPWebSocket | dict, optional
    # --- Bound connection scopes and messages; browser origins default to same origin.
    # ----------------------------------------------------------------------------------
    websocket: HTTPWebSocket | dict = field(
        default_factory=lambda: HTTPWebSocket(
            max_connections=Env.get("WEBSOCKET_MAX_CONNECTIONS", 128),
            max_message_size=Env.get("WEBSOCKET_MAX_MESSAGE_SIZE", 1024 * 1024),
            allow_origins=Env.get("WEBSOCKET_ALLOW_ORIGINS", []),
        ),
    )

    # ----------------------------------------------------------------------------------
    # proxies : HTTPProxies | dict, optional
    # --- Trusted reverse proxies allowed to supply forwarding headers.
    # ----------------------------------------------------------------------------------

    proxies: HTTPProxies | dict = field(
        default_factory=lambda: HTTPProxies(
            # --------------------------------------------------------------------------
            # trusted_proxies : list[str], optional
            # --- List of trusted proxy IP addresses or CIDR ranges.
            # --- Uses 'TRUSTED_PROXIES' env var or ['127.0.0.1'] if not set.
            # --------------------------------------------------------------------------
            trusted_proxies=Env.get("TRUSTED_PROXIES", ["127.0.0.1"]),
        ),
    )

    # ----------------------------------------------------------------------------------
    # security : HTTPSecurity | dict, optional
    # --- Allowed host names used to validate incoming requests.
    # ----------------------------------------------------------------------------------

    security: HTTPSecurity | dict = field(
        default_factory=lambda: HTTPSecurity(
            # --------------------------------------------------------------------------
            # allowed_hosts : list[str], optional
            # --- List of allowed host names for request validation.
            # --- Entries may use a leading wildcard for subdomains
            # --- (e.g. '*.example.com'). Defaults to empty list to allow all hosts.
            # --------------------------------------------------------------------------
            allowed_hosts=Env.get("ALLOWED_HOSTS", []),
        ),
    )

    # ----------------------------------------------------------------------------------
    # rate_limit : HTTPRateLimit | dict, optional
    # --- Global request limits and the time window used to count requests.
    # ----------------------------------------------------------------------------------

    rate_limit: HTTPRateLimit | dict = field(
        default_factory=lambda: HTTPRateLimit(
            # --------------------------------------------------------------------------
            # rate_limit_enabled : bool, optional
            # --- Enable or disable global rate limiting.
            # --- Uses 'RATE_LIMIT_ENABLED' env var or False if not set.
            # --------------------------------------------------------------------------
            rate_limit_enabled=Env.get("RATE_LIMIT_ENABLED", False),
            # --------------------------------------------------------------------------
            # rate_limit_requests : int, optional
            # --- Maximum number of requests allowed per time window.
            # --- Uses 'RATE_LIMIT_REQUESTS' env var or 100 if not set.
            # --------------------------------------------------------------------------
            rate_limit_requests=Env.get("RATE_LIMIT_REQUESTS", 100),
            # --------------------------------------------------------------------------
            # rate_limit_window_seconds : int, optional
            # --- Time window in seconds for rate limit counting.
            # --- Uses 'RATE_LIMIT_WINDOW' env var or 60 if not set.
            # --------------------------------------------------------------------------
            rate_limit_window_seconds=Env.get("RATE_LIMIT_WINDOW", 60),
            # --------------------------------------------------------------------------
            # rate_limit_store : str, optional
            # --- Select memory for per-process quotas or redis for shared quotas.
            # --------------------------------------------------------------------------
            rate_limit_store=Env.get("RATE_LIMIT_STORE", "memory"),
            # --------------------------------------------------------------------------
            # rate_limit_max_keys : int, optional
            # --- Reject new clients instead of evicting active memory quotas.
            # --------------------------------------------------------------------------
            rate_limit_max_keys=Env.get("RATE_LIMIT_MAX_KEYS", 10_000),
            # --------------------------------------------------------------------------
            # rate_limit_max_events : int, optional
            # --- Reject new events instead of evicting active memory quotas.
            # --------------------------------------------------------------------------
            rate_limit_max_events=Env.get("RATE_LIMIT_MAX_EVENTS", 100_000),
            # --------------------------------------------------------------------------
            # rate_limit_redis_url : str, optional
            # --- Redis URL for shared quotas; the connection is lazy.
            # --------------------------------------------------------------------------
            rate_limit_redis_url=Env.get(
                "RATE_LIMIT_REDIS_URL", "redis://127.0.0.1:6379/0",
            ),
            # --------------------------------------------------------------------------
            # rate_limit_redis_prefix : str, optional
            # --- Namespace prefix used for Redis quota keys.
            # --------------------------------------------------------------------------
            rate_limit_redis_prefix=Env.get(
                "RATE_LIMIT_REDIS_PREFIX", "orionis:http:rate-limit",
            ),
            # --------------------------------------------------------------------------
            # rate_limit_redis_timeout_seconds : int, optional
            # --- Timeout in seconds for each complete Redis attempt.
            # --------------------------------------------------------------------------
            rate_limit_redis_timeout_seconds=Env.get("RATE_LIMIT_REDIS_TIMEOUT", 1),
        ),
    )

    # ----------------------------------------------------------------------------------
    # cors : Cors | dict, optional
    # --- Cross-origin request policy and preflight response settings.
    # ----------------------------------------------------------------------------------

    cors: Cors | dict = field(
        default_factory=lambda: Cors(
            # --------------------------------------------------------------------------
            # allow_origins : list[str], optional
            # --- List of allowed origins. Defaults to [].
            # --------------------------------------------------------------------------
            allow_origins=Env.get("CORS_ALLOW_ORIGINS", []),
            # --------------------------------------------------------------------------
            # allow_origin_regex : str | None, optional
            # --- Regex pattern to match allowed origins. Defaults to None.
            # --------------------------------------------------------------------------
            allow_origin_regex=Env.get("CORS_ALLOW_ORIGIN_REGEX", None),
            # --------------------------------------------------------------------------
            # allow_methods : list[str], optional
            # --- List of allowed HTTP methods. Defaults to [].
            # --------------------------------------------------------------------------
            allow_methods=Env.get("CORS_ALLOW_METHODS", []),
            # --------------------------------------------------------------------------
            # allow_headers : list[str], optional
            # --- List of allowed HTTP headers. Defaults to [].
            # --------------------------------------------------------------------------
            allow_headers=Env.get("CORS_ALLOW_HEADERS", []),
            # --------------------------------------------------------------------------
            # expose_headers : list[str], optional
            # --- List of headers exposed to the browser. Defaults to [].
            # --------------------------------------------------------------------------
            expose_headers=Env.get("CORS_EXPOSE_HEADERS", []),
            # --------------------------------------------------------------------------
            # allow_credentials : bool, optional
            # --- Allow credentials (cookies, authorization headers). Defaults to False.
            # --------------------------------------------------------------------------
            allow_credentials=Env.get("CORS_ALLOW_CREDENTIALS", False),
            # --------------------------------------------------------------------------
            # max_age : int | None, optional
            # --- Max time in seconds to cache preflight response. Defaults to 600.
            # --------------------------------------------------------------------------
            max_age=Env.get("CORS_MAX_AGE", 600),
        ),
    )

    # ----------------------------------------------------------------------------------
    # csrf : HTTPCsrf | dict, optional
    # --- CSRF validation and the optional browser-readable XSRF cookie.
    # ----------------------------------------------------------------------------------

    csrf: HTTPCsrf | dict = field(
        default_factory=lambda: HTTPCsrf(
            # --------------------------------------------------------------------------
            # enabled : bool, optional
            # --- Enable or disable CSRF validation for all web routes.
            # --- Uses 'CSRF_ENABLED' env var or True if not set.
            # --------------------------------------------------------------------------
            enabled=Env.get("CSRF_ENABLED", True),
            # --------------------------------------------------------------------------
            # token_length : int, optional
            # --- Byte length of the generated CSRF token.
            # --- 32 bytes = 256 bits of entropy (minimum recommended).
            # --------------------------------------------------------------------------
            token_length=Env.get("CSRF_TOKEN_LENGTH", 32),
            # --------------------------------------------------------------------------
            # session_key : str, optional
            # --- Session key under which the CSRF token is stored.
            # --- Defaults to '_csrf_token'.
            # --------------------------------------------------------------------------
            session_key=Env.get("CSRF_SESSION_KEY", "_csrf_token"),
            # --------------------------------------------------------------------------
            # xsrf_cookie : bool, optional
            # --- Set a readable XSRF-TOKEN cookie (Angular / Axios pattern).
            # --- Uses 'CSRF_XSRF_COOKIE' env var or False if not set.
            # --------------------------------------------------------------------------
            xsrf_cookie=Env.get("CSRF_XSRF_COOKIE", False),
            # --------------------------------------------------------------------------
            # cookie_name : str, optional
            # --- Name of the XSRF double-submit cookie. Defaults to 'XSRF-TOKEN'.
            # --------------------------------------------------------------------------
            cookie_name=Env.get("CSRF_COOKIE_NAME", "XSRF-TOKEN"),
            # --------------------------------------------------------------------------
            # cookie_secure : bool, optional
            # --- Force the Secure flag on the XSRF cookie.
            # --- Automatically promoted to True on HTTPS regardless.
            # --------------------------------------------------------------------------
            cookie_secure=Env.get("CSRF_COOKIE_SECURE", False),
            # --------------------------------------------------------------------------
            # cookie_same_site : str, optional
            # --- SameSite policy: 'lax', 'strict', or 'none'. Defaults to 'lax'.
            # --------------------------------------------------------------------------
            cookie_same_site=Env.get("CSRF_COOKIE_SAME_SITE", "lax"),
            # --------------------------------------------------------------------------
            # cookie_path : str, optional
            # --- Path attribute for the XSRF cookie. Defaults to '/'.
            # --------------------------------------------------------------------------
            cookie_path=Env.get("CSRF_COOKIE_PATH", "/"),
            # --------------------------------------------------------------------------
            # cookie_domain : str | None, optional
            # --- Domain attribute for the XSRF cookie. None omits it.
            # --------------------------------------------------------------------------
            cookie_domain=Env.get("CSRF_COOKIE_DOMAIN", None),
        ),
    )
