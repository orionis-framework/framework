from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.database.enums import PGSQLCharset, PGSQLSSLMode
from orionis.environment.facade import Env
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
        default_factory=lambda: Env.get("DB_CHARSET", PGSQLCharset.UTF8.value),
        metadata={
            "description": "Database charset",
            "default": PGSQLCharset.UTF8.value,
        },
    )

    prefix: str = field(
        default="",
        metadata={
            "description": "Table prefix",
            "default": "",
        },
    )

    prefix_indexes: bool = field(
        default=True,
        metadata={
            "description": "Whether to prefix indexes",
            "default": True,
        },
    )

    search_path: str = field(
        default="public",
        metadata={
            "description": "PostgreSQL schema search_path",
            "default": "public",
        },
    )

    sslmode: str | PGSQLSSLMode = field(
        default=PGSQLSSLMode.PREFER.value,
        metadata={
            "description": "Connection SSL mode",
            "default": PGSQLSSLMode.PREFER.value,
        },
    )

    def __validateCharset(self) -> None:
        """
        Validate and normalize the `charset` attribute.

        Ensures the `charset` attribute is a valid option from PGSQLCharset.
        Converts string representations to their enum value.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the `charset` attribute is not a valid option.
        """
        # Validate `charset` attribute against allowed enum options
        options_charset = PGSQLCharset._member_names_
        if isinstance(self.charset, str):
            # Normalize and validate charset string
            _value = self.charset.upper().strip()
            if _value not in options_charset:
                error_msg = (
                    "The 'charset' attribute must be a valid option "
                    f"{PGSQLCharset._member_names_!s}"
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "charset", PGSQLCharset[_value].value)
        else:
            object.__setattr__(self, "charset", self.charset.value)

    def __validateSSLMode(self) -> None:
        """
        Validate and normalize the `sslmode` attribute.

        Ensures the `sslmode` attribute is a valid option from PGSQLSSLMode.
        Converts string representations to their enum value.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the `sslmode` attribute is not a valid option.
        """
        # Validate `sslmode` attribute
        if not isinstance(self.sslmode, (str, PGSQLSSLMode)):
            error_msg = (
                "The 'sslmode' attribute must be a string or PGSQLSSLMode. "
                f"Received: {self.sslmode!r}"
            )
            raise TypeError(error_msg)

        # Validate and normalize `sslmode` attribute
        options_sslmode = PGSQLSSLMode._member_names_
        if isinstance(self.sslmode, str):
            # Normalize and validate sslmode string
            _value = self.sslmode.upper().strip()
            if _value not in options_sslmode:
                error_msg = (
                    "The 'sslmode' attribute must be a valid option "
                    f"{PGSQLSSLMode._member_names_!s}"
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "sslmode", PGSQLSSLMode[_value].value)
        else:
            object.__setattr__(self, "sslmode", self.sslmode.value)

    def __post_init__(self) -> None:
        """
        Validate and initialize the database entity attributes.

        Ensures all attributes are of the correct type and value. Converts string
        representations of enums to their values.

        Parameters
        ----------
        self : PGSQL
            The instance of the PGSQL configuration entity.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If a required attribute is missing or invalid.
        TypeError
            If an attribute is of incorrect type.
        """
        # Call parent post-initialization
        super().__post_init__()

        # Validate `driver` attribute
        if not isinstance(self.driver, str) or not self.driver:
            error_msg = (
                "The 'driver' attribute must be a non-empty string. "
                f"Received: {self.driver!r}"
            )
            raise ValueError(error_msg)

        # Validate `host` attribute
        if not isinstance(self.host, str) or not self.host.strip():
            error_msg = (
                "The 'host' attribute must be a non-empty string. "
                f"Received: {self.host!r}"
            )
            raise ValueError(error_msg)

        # Validate `port` attribute
        if not (isinstance(self.port, (str, int)) and str(self.port).isdigit()):
            error_msg = (
                "The 'port' attribute must be a numeric string or integer. "
                f"Received: {self.port!r}"
            )
            raise TypeError(error_msg)

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
                "The 'prefix' attribute must be a string. "
                f"Received: {self.prefix!r}"
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
