from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.session.enums import SameSitePolicy
from orionis.foundation.config.session.enums.drivers import SessionDriver
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

# Pre-computed frozensets enable O(1) membership tests at validation time.
_SAME_SITE_VALUES: frozenset[str] = frozenset(p.value for p in SameSitePolicy)
_DRIVER_VALUES: frozenset[str] = frozenset(d.value for d in SessionDriver)

# Characters forbidden inside a cookie name per RFC 6265 §4.1.1.
_INVALID_COOKIE_CHARS: frozenset[str] = frozenset(" ;,")

@dataclass(frozen=True, kw_only=True)
class Session(BaseEntity):
    """
    Configure the session middleware.

    Parameters
    ----------
    driver : str | SessionDriver
        Session driver. Defaults to SessionDriver.MEMORY.
    lifetime : int
        Session lifetime in minutes. Defaults to 120.
    expire_on_close : bool
        Expire session on browser close (omits Max-Age). Defaults to False.
    files : str | None
        Path to session files (file driver). Defaults to 'storage/framework/sessions'.
    connection : str | None
        Database connection for session storage (database driver). Defaults to None.
    table : str | None
        Database table for session storage (database driver). Defaults to 'sessions'.
    cache : str | None
        Cache store for session storage (cache driver). Defaults to None.
    cookie : str
        Name of the session cookie. Defaults to 'sessionid'.
    path : str
        Cookie path. Defaults to '/'.
    domain : str | None
        Cookie domain for cross-subdomain usage.
    secure : bool
        Restrict cookies to HTTPS. Defaults to False.
    http_only : bool
        Prevent JavaScript from accessing the cookie. Defaults to True.
    same_site : str | SameSitePolicy
        SameSite cookie policy. Defaults to SameSitePolicy.LAX.
    partitioned : bool
        Enable CHIPS (partitioned) cookies. Defaults to False.

    Returns
    -------
    None
        This class does not return a value.
    """

    driver: str | SessionDriver = field(
        default_factory=lambda: Env.get("SESSION_DRIVER", SessionDriver.MEMORY),
        metadata={
            "description": "Session driver.",
            "default": SessionDriver.MEMORY.value,
        },
    )

    lifetime: int = field(
        default_factory=lambda: Env.get("SESSION_LIFETIME", 120),
        metadata={
            "description": "Session lifetime in minutes.",
            "default": 120,
        },
    )

    expire_on_close: bool = field(
        default_factory=lambda: Env.get("SESSION_EXPIRE_ON_CLOSE", False),
        metadata={
            "description": "Expire session on browser close (omits Max-Age).",
            "default": False,
        },
    )

    # File-driver: directory where session files are stored.
    files: str | None = field(
        default_factory=lambda: Env.get("SESSION_FILES", "storage/framework/sessions"),
        metadata={
            "description": "Path to session files.",
            "default": "storage/framework/sessions",
        },
    )

    # Database-driver: connection name used to persist session records.
    connection: str | None = field(
        default_factory=lambda: Env.get("DB_CONNECTION"),
        metadata={
            "description": "Database connection for session storage.",
            "default": None,
        },
    )

    # Database-driver: table name used to persist session records.
    table: str | None = field(
        default_factory=lambda: Env.get("SESSION_TABLE", "sessions"),
        metadata={
            "description": "Database table for session storage.",
            "default": "sessions",
        },
    )

    # Cache-driver: named cache store used to persist session records.
    cache: str | None = field(
        default_factory=lambda: Env.get("CACHE_STORE"),
        metadata={
            "description": "Cache store for session storage.",
            "default": None,
        },
    )

    cookie: str = field(
        default_factory=lambda: Env.get("SESSION_COOKIE", "sessionid"),
        metadata={
            "description": "Name of the session cookie.",
            "default": "sessionid",
        },
    )

    path: str = field(
        default_factory=lambda: Env.get("SESSION_PATH", "/"),
        metadata={
            "description": "Cookie path.",
            "default": "/",
        },
    )

    domain: str | None = field(
        default_factory=lambda: Env.get("SESSION_DOMAIN"),
        metadata={
            "description": "Cookie domain for cross-subdomain usage.",
            "default": None,
        },
    )

    secure: bool = field(
        default_factory=lambda: Env.get("SESSION_SECURE", False),
        metadata={
            "description": "Restrict cookies to HTTPS.",
            "default": False,
        },
    )

    http_only: bool = field(
        default_factory=lambda: Env.get("SESSION_HTTP_ONLY", True),
        metadata={
            "description": "Prevent JavaScript from accessing the cookie.",
            "default": True,
        },
    )

    same_site: str | SameSitePolicy = field(
        default_factory=lambda: Env.get("SESSION_SAME_SITE", SameSitePolicy.LAX.value),
        metadata={
            "description": "SameSite cookie policy.",
            "default": SameSitePolicy.LAX.value,
        },
    )

    partitioned: bool = field(
        default_factory=lambda: Env.get("SESSION_PARTITIONED", False),
        metadata={
            "description": "Partition session data by user.",
            "default": False,
        },
    )

    def __validateDriver(self) -> None:
        """
        Normalise and validate the *driver* field.

        Accept a ``SessionDriver`` enum member or a plain string
        matching a recognised driver name (case-insensitive).  When a
        valid string is supplied it is coerced to the corresponding
        ``SessionDriver`` member via ``object.__setattr__``.

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            Mutates *driver* in-place when a plain string is given.

        Raises
        ------
        ValueError
            If the string does not match any registered driver name.
        TypeError
            If the value is neither a ``str`` nor a ``SessionDriver``.
        """
        # Enum member already validated - nothing further required.
        if isinstance(self.driver, SessionDriver):
            return

        # Normalise the string and verify it is a known driver value.
        if isinstance(self.driver, str):
            normalized = self.driver.lower().strip()
            if normalized not in _DRIVER_VALUES:
                error_msg = (
                    "driver must be one of: "
                    f"{', '.join(sorted(_DRIVER_VALUES))}"
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "driver", SessionDriver(normalized))
            return

        # Any other type is rejected.
        error_msg = "driver must be a string or SessionDriver"
        raise TypeError(error_msg)

    def __validateCookie(self) -> None:
        """
        Validate the *cookie* name field.

        Ensure the name is a non-empty string that contains no
        characters forbidden by RFC 6265 (spaces, semicolons, commas).

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            No value is returned.

        Raises
        ------
        ValueError
            If the name is empty or contains forbidden characters.
        """
        # Cookie name must be a non-empty string.
        if not isinstance(self.cookie, str) or not self.cookie.strip():
            error_msg = "cookie must be a non-empty string"
            raise ValueError(error_msg)

        # Reject characters that would break the Set-Cookie header.
        if any(c in _INVALID_COOKIE_CHARS for c in self.cookie):
            error_msg = (
                "cookie must not contain spaces, semicolons, or commas"
            )
            raise ValueError(error_msg)

    def __validateLifetime(self) -> None:
        """
        Validate the *lifetime* field.

        The lifetime represents the server-side session duration in
        minutes and must be a strictly positive integer.

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            No value is returned.

        Raises
        ------
        TypeError
            If *lifetime* is not an ``int``.
        ValueError
            If *lifetime* is not strictly greater than zero.
        """
        # Guard against floats or other numeric types from env parsing.
        if not isinstance(self.lifetime, int):
            error_msg = "lifetime must be a positive integer"
            raise TypeError(error_msg)

        # Zero or negative lifetimes are semantically invalid.
        if self.lifetime <= 0:
            error_msg = "lifetime must be a positive integer"
            raise ValueError(error_msg)

    def __validateBooleans(self) -> None:
        """
        Validate all boolean fields in a single pass.

        Iterate over every boolean field and raise on the first value
        that is not a ``bool`` instance.

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            No value is returned.

        Raises
        ------
        TypeError
            If any boolean field holds a non-boolean value.
        """
        # Centralise bool checks to avoid repetitive isinstance calls.
        _bool_fields = (
            "expire_on_close",
            "secure",
            "http_only",
            "partitioned",
        )
        for name in _bool_fields:
            if not isinstance(getattr(self, name), bool):
                error_msg = f"{name} must be a boolean value"
                raise TypeError(error_msg)

    def __validateSameSite(self) -> None:
        """
        Normalise and validate the *same_site* field.

        Accept a ``SameSitePolicy`` member or a plain string.  The
        stored value is always the canonical lowercase string form of
        the policy (e.g. ``"lax"``).

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            Mutates *same_site* in-place to its canonical string form.

        Raises
        ------
        ValueError
            If the string is not a valid ``SameSitePolicy`` value.
        TypeError
            If the value is neither a ``str`` nor a ``SameSitePolicy``.
        """
        # Enum member: extract its canonical lowercase string value.
        if isinstance(self.same_site, SameSitePolicy):
            object.__setattr__(self, "same_site", self.same_site.value)
            return

        # String: normalise to lowercase and verify membership.
        if isinstance(self.same_site, str):
            normalized = self.same_site.lower().strip()
            if normalized not in _SAME_SITE_VALUES:
                error_msg = (
                    "same_site must be one of: "
                    f"{', '.join(sorted(_SAME_SITE_VALUES))}"
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "same_site", normalized)
            return

        # Any other type is rejected.
        error_msg = "same_site must be a string or SameSitePolicy"
        raise TypeError(error_msg)

    def __validatePath(self) -> None:
        """
        Validate the *path* field.

        The cookie path must be a string that begins with ``'/'`` as
        required by RFC 6265 §4.1.1.

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            No value is returned.

        Raises
        ------
        ValueError
            If *path* is not a string or does not start with ``'/'``.
        """
        # RFC 6265: the path-value must start with a slash.
        if not isinstance(self.path, str) or not self.path.startswith("/"):
            error_msg = "path must be a string starting with '/'"
            raise ValueError(error_msg)

    def __validateDomain(self) -> None:
        """
        Validate the *domain* field.

        When provided the domain must be a non-empty string that does
        not begin or end with a dot and contains no consecutive dots.

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            No value is returned.

        Raises
        ------
        ValueError
            If *domain* is an empty string or violates dot rules.
        """
        # None means no domain restriction is applied.
        if self.domain is None:
            return

        # Reject blank strings or wrong types.
        if not isinstance(self.domain, str) or not self.domain.strip():
            error_msg = "domain must be a non-empty string or None"
            raise ValueError(error_msg)

        # Leading/trailing dots break browser cookie matching.
        if self.domain.startswith(".") or self.domain.endswith("."):
            error_msg = "domain must not start or end with a dot"
            raise ValueError(error_msg)

        # Consecutive dots indicate a malformed domain label.
        if ".." in self.domain:
            error_msg = "domain must not contain consecutive dots"
            raise ValueError(error_msg)

    def __validateFiles(self) -> None:
        """
        Validate the *files* path field.

        When provided the value must be a non-empty string pointing to
        the directory used by the file session driver.

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            No value is returned.

        Raises
        ------
        ValueError
            If *files* is provided but is not a non-empty string.
        """
        # None means the driver will use its built-in default path.
        if self.files is None:
            return

        # Reject blank strings or wrong types.
        if not isinstance(self.files, str) or not self.files.strip():
            error_msg = "files must be a non-empty string or None"
            raise ValueError(error_msg)

    def __validateConnection(self) -> None:
        """
        Validate the *connection* field.

        When provided the value must be a non-empty string naming a
        database connection (database driver).

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            No value is returned.

        Raises
        ------
        ValueError
            If *connection* is provided but is not a non-empty string.
        """
        # None means the driver will use the default database connection.
        if self.connection is None:
            return

        # Reject blank strings or wrong types.
        if not isinstance(self.connection, str) or not self.connection.strip():
            error_msg = "connection must be a non-empty string or None"
            raise ValueError(error_msg)

    def __validateTable(self) -> None:
        """
        Validate the *table* field.

        When provided the value must be a non-empty string naming the
        database table used to persist session records (database driver).

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            No value is returned.

        Raises
        ------
        ValueError
            If *table* is provided but is not a non-empty string.
        """
        # None means the driver will use its built-in default table name.
        if self.table is None:
            return

        # Reject blank strings or wrong types.
        if not isinstance(self.table, str) or not self.table.strip():
            error_msg = "table must be a non-empty string or None"
            raise ValueError(error_msg)

    def __validateCache(self) -> None:
        """
        Validate the *cache* field.

        When provided the value must be a non-empty string naming a
        cache store (cache driver).

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            No value is returned.

        Raises
        ------
        ValueError
            If *cache* is provided but is not a non-empty string.
        """
        # None means the driver will use the default cache store.
        if self.cache is None:
            return

        # Reject blank strings or wrong types.
        if not isinstance(self.cache, str) or not self.cache.strip():
            error_msg = "cache must be a non-empty string or None"
            raise ValueError(error_msg)

    def __post_init__(self) -> None:
        """Validate all fields after dataclass initialisation.

        Called automatically by the dataclass machinery immediately
        after ``__init__``.  Delegates to individual field validators
        in a deterministic order.

        Parameters
        ----------
        self : Session
            The Session instance being validated.

        Returns
        -------
        None
            No value is returned.
        """
        # Allow the base class to run its own post-init logic first.
        super().__post_init__()

        # Run each field validator in dependency order.
        self.__validateDriver()
        self.__validateCookie()
        self.__validateLifetime()
        self.__validateBooleans()
        self.__validateSameSite()
        self.__validatePath()
        self.__validateDomain()
        self.__validateFiles()
        self.__validateConnection()
        self.__validateTable()
        self.__validateCache()


