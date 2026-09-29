from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.database.enums import PGSQLCharset, PGSQLSSLMode
from orionis.foundation.config.validation import normalize_enum, validate_integer
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class PGSQL(BaseEntity):
    """
    Represent a PostgreSQL database configuration entity.

    Attributes
    ----------
    driver : str
        Database driver type.
    host : str
        Database host.
    port : str | int
        Database port.
    database : str
        Database name.
    username : str
        Database user.
    password : str
        Database password.
    charset : str | PGSQLCharset
        Database charset.
    prefix : str
        Table prefix.
    prefix_indexes : bool
        Whether to prefix indexes.
    search_path : str
        PostgreSQL schema search_path.
    sslmode : str | PGSQLSSLMode
        Connection SSL mode.
    """

    driver: str = field(
        default="pgsql",
        metadata={
            "description": "Database driver type",
            "default": "pgsql",
        },
    )

    host: str = field(
        default_factory=lambda: Env.get("DB_HOST", "127.0.0.1"),
        metadata={
            "description": "Database host",
            "default": "127.0.0.1",
        },
    )

    port: str | int = field(
        default_factory=lambda: Env.get("DB_PORT", 5432),
        metadata={
            "description": "Database port",
            "default": 5432,
        },
    )

    database: str = field(
        default_factory=lambda: Env.get("DB_DATABASE", "orionis"),
        metadata={
            "description": "Database name",
            "default": "orionis",
        },
    )

    username: str = field(
        default_factory=lambda: Env.get("DB_USERNAME", "postgres"),
        metadata={
            "description": "Database user",
            "default": "postgres",
        },
    )

    password: str = field(
        default_factory=lambda: Env.get("DB_PASSWORD", ""),
        metadata={
            "description": "Database password",
            "default": "",
        },
    )

    charset: str | PGSQLCharset = field(
        default_factory=lambda: (
            Env.get("DB_CHARSET", PGSQLCharset.UTF8.value)
            if str(Env.get("DB_CONNECTION", "sqlite")).strip().lower() == "pgsql"
            else PGSQLCharset.UTF8.value
        ),
        metadata={
            "description": "Database charset",
            "default": "UTF8",
        },
    )

    prefix: str = field(
        default_factory=lambda: Env.get("DB_PREFIX", ""),
        metadata={
            "description": "Table prefix",
            "default": "",
        },
    )

    prefix_indexes: bool = field(
        default_factory=lambda: Env.get("DB_PREFIX_INDEXES", True),
        metadata={
            "description": "Whether to prefix indexes",
            "default": True,
        },
    )

    search_path: str = field(
        default_factory=lambda: Env.get("DB_SEARCH_PATH", "public"),
        metadata={
            "description": "PostgreSQL schema search_path",
            "default": "public",
        },
    )

    sslmode: str | PGSQLSSLMode = field(
        default_factory=lambda: Env.get("DB_SSLMODE", PGSQLSSLMode.PREFER.value),
        metadata={
            "description": "Connection SSL mode",
            "default": PGSQLSSLMode.PREFER.value,
        },
    )

    def __validateCharset(self: PGSQL) -> None:
        """
        Normalize the PostgreSQL charset option.

        Parameters
        ----------
        self : PGSQL
            Configuration entity containing the charset to normalize.

        Returns
        -------
        None
            This method stores the canonical charset value in the entity.
        """
        # Store the canonical enum value for the configured charset.
        object.__setattr__(
            self,
            "charset",
            normalize_enum(
                self.charset,
                PGSQLCharset,
                "charset",
            ),
        )

    def __validateSSLMode(self: PGSQL) -> None:
        """
        Normalize the PostgreSQL SSL mode option.

        Parameters
        ----------
        self : PGSQL
            Configuration entity containing the SSL mode to normalize.

        Returns
        -------
        None
            This method stores the canonical SSL mode value in the entity.
        """
        # Store the canonical enum value for the configured SSL mode.
        object.__setattr__(
            self,
            "sslmode",
            normalize_enum(
                self.sslmode,
                PGSQLSSLMode,
                "sslmode",
            ),
        )

    def __post_init__(self: PGSQL) -> None:
        """
        Validate and initialize the PostgreSQL configuration attributes.

        Validate scalar settings, normalize enum values, and preserve the
        configured port representation after range validation.

        Parameters
        ----------
        self : PGSQL
            Configuration entity to validate and initialize.

        Returns
        -------
        None
            This method validates and normalizes the entity in place.

        Raises
        ------
        ValueError
            If a required attribute is missing or has an invalid value.
        TypeError
            If an attribute has an invalid type.
        """
        # Call parent post-initialization
        super().__post_init__()

        # Validate `driver` attribute
        if self.driver != "pgsql":
            error_msg = "The 'driver' property must be 'pgsql'."
            raise ValueError(error_msg)

        # Validate `host` attribute
        if not isinstance(self.host, str) or not self.host.strip():
            error_msg = (
                "The 'host' attribute must be a non-empty string. "
                f"Received: {self.host!r}"
            )
            raise ValueError(error_msg)

        # Validate `port` attribute
        port = self.port
        if isinstance(port, str) and port.isascii() and port.isdecimal():
            port = int(port)
        validate_integer(port, "port", minimum=1, maximum=65535)

        # Validate `database` attribute
        if not isinstance(self.database, str) or not self.database.strip():
            error_msg = (
                "The 'database' attribute must be a non-empty string. "
                f"Received: {self.database!r}"
            )
            raise ValueError(error_msg)

        # Validate `username` attribute
        if not isinstance(self.username, str) or not self.username.strip():
            error_msg = (
                "The 'username' attribute must be a non-empty string. "
                f"Received: {self.username!r}"
            )
            raise ValueError(error_msg)

        # Validate `password` attribute
        if not isinstance(self.password, str):
            error_msg = (
                "The 'password' attribute must be a string. "
                f"Received: {self.password!r}"
            )
            raise TypeError(error_msg)

        # Validate `charset` attribute
        self.__validateCharset()

        # Validate `prefix` attribute
        if not isinstance(self.prefix, str):
            error_msg = (
                f"The 'prefix' attribute must be a string. Received: {self.prefix!r}"
            )
            raise TypeError(error_msg)

        # Validate `prefix_indexes` attribute
        if not isinstance(self.prefix_indexes, bool):
            error_msg = (
                "The 'prefix_indexes' attribute must be boolean. "
                f"Received: {self.prefix_indexes!r}"
            )
            raise TypeError(error_msg)

        # Validate `search_path` attribute
        if not isinstance(self.search_path, str) or not self.search_path.strip():
            error_msg = (
                "The 'search_path' attribute must be a non-empty string. "
                f"Received: {self.search_path!r}"
            )
            raise ValueError(error_msg)

        # Validate and normalize `sslmode` attribute
        self.__validateSSLMode()
