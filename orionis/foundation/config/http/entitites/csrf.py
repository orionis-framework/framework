from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from orionis.environment import Env
from orionis.foundation.config.validation import validate_boolean, validate_cookie_name
from orionis.support.entities.base import BaseEntity

_MIN_TOKEN_LENGTH = 32

@dataclass(frozen=True, kw_only=True)
class HTTPCsrf(BaseEntity):
    """
    CSRF protection configuration for web routes.

    Attributes
    ----------
    enabled : bool
        Enable or disable CSRF validation globally. Defaults to ``True``.
    token_length : int
        Number of random bytes used to generate the token via
        ``secrets.token_urlsafe``. 32 bytes yields 256 bits of entropy
        (43 URL-safe characters). Defaults to ``32``.
    session_key : str
        Session key under which the token is stored. Defaults to
        ``"_csrf_token"``.
    xsrf_cookie : bool
        When ``True``, set a readable ``XSRF-TOKEN`` cookie on every
        response so that JavaScript clients (Angular, Axios) can
        forward it as ``X-XSRF-Token``. Defaults to ``False``.
    cookie_name : str
        Name of the XSRF cookie. Defaults to ``"XSRF-TOKEN"``.
    cookie_secure : bool
        Set the ``Secure`` attribute on the XSRF cookie. When
        ``False``, the middleware automatically promotes the flag to
        ``True`` on HTTPS requests. Defaults to ``False``.
    cookie_same_site : Literal["lax", "strict", "none"]
        ``SameSite`` attribute for the XSRF cookie. Defaults to
        ``"lax"``.
    cookie_path : str
        ``Path`` attribute for the XSRF cookie. Defaults to ``"/"``.
    cookie_domain : str | None
        ``Domain`` attribute for the XSRF cookie. ``None`` omits it.
        Defaults to ``None``.
    """

    # Global toggle enabling or disabling CSRF validation
    enabled: bool = field(
        default_factory=lambda: Env.get("CSRF_ENABLED", True),
        metadata={
            "description": "Enable or disable CSRF validation globally.",
            "default": True,
        },
    )

    # Entropy byte length used when generating tokens via secrets.token_urlsafe
    token_length: int = field(
        default_factory=lambda: Env.get("CSRF_TOKEN_LENGTH", 32),
        metadata={
            "description": (
                "Byte length for token generation via secrets.token_urlsafe. "
                "32 bytes = 256 bits of entropy."
            ),
            "default": 32,
        },
    )

    # Session key under which the generated CSRF token is persisted
    session_key: str = field(
        default_factory=lambda: Env.get("CSRF_SESSION_KEY", "_csrf_token"),
        metadata={
            "description": "Session key under which the CSRF token is stored.",
            "default": "_csrf_token",
        },
    )

    # Flag to emit a readable XSRF-TOKEN cookie for JS framework clients
    xsrf_cookie: bool = field(
        default_factory=lambda: Env.get("CSRF_XSRF_COOKIE", False),
        metadata={
            "description": (
                "When True, set a readable XSRF-TOKEN cookie for Angular / Axios "
                "double-submit pattern."
            ),
            "default": False,
        },
    )

    # HTTP cookie name delivered to the browser
    cookie_name: str = field(
        default_factory=lambda: Env.get("CSRF_COOKIE_NAME", "XSRF-TOKEN"),
        metadata={
            "description": "Name of the XSRF double-submit cookie.",
            "default": "XSRF-TOKEN",
        },
    )

    # Whether to enforce the Secure attribute on the XSRF cookie
    cookie_secure: bool = field(
        default_factory=lambda: Env.get("CSRF_COOKIE_SECURE", False),
        metadata={
            "description": (
                "Force the Secure flag on the XSRF cookie. "
                "Automatically set to True on HTTPS requests regardless."
            ),
            "default": False,
        },
    )

    # SameSite policy controlling cross-site cookie delivery
    cookie_same_site: Literal["lax", "strict", "none"] = field(
        default_factory=lambda: Env.get("CSRF_COOKIE_SAME_SITE", "lax"),
        metadata={
            "description": "SameSite policy for the XSRF cookie.",
            "default": "lax",
        },
    )

    # URL path scope restricting where the cookie is sent
    cookie_path: str = field(
        default_factory=lambda: Env.get("CSRF_COOKIE_PATH", "/"),
        metadata={
            "description": "Path attribute for the XSRF cookie.",
            "default": "/",
        },
    )

    # Optional domain scope; None omits the Domain attribute entirely
    cookie_domain: str | None = field(
        default_factory=lambda: Env.get("CSRF_COOKIE_DOMAIN", None),
        metadata={
            "description": "Domain attribute for the XSRF cookie. None omits it.",
            "default": None,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate all CSRF configuration fields after dataclass construction.

        Raises
        ------
        TypeError
            If any field has an unexpected type.
        ValueError
            If ``token_length`` is below the minimum secure threshold or
            any string field is empty or otherwise invalid.

        Returns
        -------
        None
            No value is returned; validation runs as a side effect.
        """
        # Delegate shared base validation before running CSRF-specific checks
        super().__post_init__()

        # Run each field validator in declaration order
        self.__validateEnabled()
        self.__validateTokenLength()
        self.__validateSessionKey()
        self.__validateXsrfCookie()
        validate_boolean(self.cookie_secure, "cookie_secure")
        self.__validateCookieName()
        self.__validateCookieSameSite()
        self.__validateCookiePath()
        self.__validateCookieDomain()
        if (
            self.xsrf_cookie
            and self.cookie_same_site == "none"
            and not self.cookie_secure
        ):
            message = "SameSite none requires a secure XSRF cookie."
            raise ValueError(message)

    def __validateEnabled(self) -> None:
        """
        Validate that ``enabled`` is a boolean.

        Raises
        ------
        TypeError
            If ``enabled`` is not a ``bool`` instance.

        Returns
        -------
        None
            No value is returned; raises on invalid input.
        """
        # Reject non-boolean values for the global CSRF toggle
        if not isinstance(self.enabled, bool):
            error_msg = "Invalid type for 'enabled': expected a boolean."
            raise TypeError(error_msg)

    def __validateTokenLength(self) -> None:
        """
        Validate that ``token_length`` is a plain integer >= 32.

        Raises
        ------
        TypeError
            If ``token_length`` is not a plain ``int``
            (``bool`` subclass is excluded).
        ValueError
            If ``token_length`` is below 32 (minimum 256 bits of entropy).

        Returns
        -------
        None
            No value is returned; raises on invalid input.
        """
        # bool subclasses int; exclude it to prevent True/False being accepted
        if not isinstance(self.token_length, int) or isinstance(
            self.token_length,
            bool,
        ):
            error_msg = "Invalid type for 'token_length': expected an integer."
            raise TypeError(error_msg)

        # Enforce minimum entropy threshold: 32 bytes = 256 bits
        if self.token_length < _MIN_TOKEN_LENGTH:
            error_msg = "Invalid value for 'token_length': minimum 32 bytes (256 bits)."
            raise ValueError(error_msg)

    def __validateSessionKey(self) -> None:
        """
        Validate that ``session_key`` is a non-empty string.

        Raises
        ------
        ValueError
            If ``session_key`` is not a string or is an empty string.

        Returns
        -------
        None
            No value is returned; raises on invalid input.
        """
        # Empty keys would silently overwrite unrelated session entries
        if not isinstance(self.session_key, str) or not self.session_key.strip():
            error_msg = "Invalid value for 'session_key': expected a non-empty string."
            raise ValueError(error_msg)

    def __validateXsrfCookie(self) -> None:
        """
        Validate that ``xsrf_cookie`` is a boolean.

        Raises
        ------
        TypeError
            If ``xsrf_cookie`` is not a ``bool`` instance.

        Returns
        -------
        None
            No value is returned; raises on invalid input.
        """
        # Guard against accidental truthy/falsy non-bool values
        if not isinstance(self.xsrf_cookie, bool):
            error_msg = "Invalid type for 'xsrf_cookie': expected a boolean."
            raise TypeError(error_msg)

    def __validateCookieName(self) -> None:
        """
        Validate that ``cookie_name`` is acceptable by the response cookie serializer.

        Raises
        ------
        ValueError
            If ``cookie_name`` is not valid.

        Returns
        -------
        None
            No value is returned; raises on invalid input.
        """
        validate_cookie_name(self.cookie_name, "cookie_name")

    def __validateCookieSameSite(self) -> None:
        """
        Validate that ``cookie_same_site`` is a recognised SameSite value.

        Raises
        ------
        ValueError
            If ``cookie_same_site`` is not one of ``"lax"``,
            ``"strict"``, or ``"none"``.

        Returns
        -------
        None
            No value is returned; raises on invalid input.
        """
        # Only the three RFC-defined SameSite tokens are permitted
        valid = {"lax", "strict", "none"}
        if (
            not isinstance(self.cookie_same_site, str)
            or self.cookie_same_site not in valid
        ):
            error_msg = (
                f"Invalid value for 'cookie_same_site': must be one of {valid!r}."
            )
            raise ValueError(error_msg)

    def __validateCookiePath(self) -> None:
        """
        Validate that ``cookie_path`` is a string.

        Raises
        ------
        TypeError
            If ``cookie_path`` is not a ``str`` instance.

        Returns
        -------
        None
            No value is returned; raises on invalid input.
        """
        # Path must be a string; an empty string is a valid browser default
        if not isinstance(self.cookie_path, str):
            error_msg = "Invalid type for 'cookie_path': expected a string."
            raise TypeError(error_msg)

    def __validateCookieDomain(self) -> None:
        """
        Validate that ``cookie_domain`` is a string or ``None``.

        Raises
        ------
        TypeError
            If ``cookie_domain`` is neither a ``str`` nor ``None``.

        Returns
        -------
        None
            No value is returned; raises on invalid input.
        """
        # None omits the Domain attribute from the Set-Cookie header
        if self.cookie_domain is not None and not isinstance(
            self.cookie_domain,
            str,
        ):
            error_msg = "Invalid type for 'cookie_domain': expected a string or None."
            raise TypeError(error_msg)
