from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.database.enums.sqlserver_charset import (
    SQLServerCharset,
)
from orionis.foundation.config.validation import normalize_enum, validate_boolean
from orionis.support.entities.base import BaseEntity

# Valid TCP port boundary for the SQL Server listener.
_MAX_PORT: int = 65535

@dataclass(frozen=True, kw_only=True)
class SQLServer(BaseEntity):
    """
    Represent the Microsoft SQL Server database configuration.

    Attributes
    ----------
    driver : str
        The database driver being used, e.g., 'sqlserver'.
    host : str
        The host address for the SQL Server instance.
    port : int
        The port for connecting to SQL Server (default 1433).
    database : str
        The name of the SQL Server database.
    username : str
        The username for connecting to the database.
    password : str
        The password for the database.
    charset : str
        The charset used for the connection.
    prefix : str
        Prefix for table names.
    prefix_indexes : bool
        Whether to prefix index names.
    encrypt : bool | str
        Whether the connection must be encrypted ('yes'/'no' or bool).
    trust_server_certificate : bool
        Whether to trust the server certificate without validation.
    odbc_driver : str
        Name of the ODBC driver used by the connection.
    """

    driver: str = field(
        default="sqlserver",
        metadata={
            "description": "The database driver being used.",
            "default": "sqlserver",
        },
    )

    host: str = field(
        default_factory=lambda: Env.get("DB_HOST", "127.0.0.1"),
        metadata={
            "description": "The host address for the SQL Server instance.",
            "default": "127.0.0.1",
        },
    )

    port: int = field(
        default_factory=lambda: Env.get("DB_PORT", 1433),
        metadata={
            "description": "The port for connecting to SQL Server.",
            "default": 1433,
        },
    )

    database: str = field(
        default_factory=lambda: Env.get("DB_DATABASE", "orionis"),
        metadata={
            "description": "The name of the SQL Server database.",
            "default": "orionis",
        },
    )

    username: str = field(
        default_factory=lambda: Env.get("DB_USERNAME", "sa"),
        metadata={
            "description": "The username for connecting to the database.",
            "default": "sa",
        },
    )

    password: str = field(
        default_factory=lambda: Env.get("DB_PASSWORD", ""),
        metadata={
            "description": "The password for the database.",
            "default": "",
        },
    )

    charset: SQLServerCharset | str = field(
        default_factory=lambda: (
            Env.get("DB_CHARSET", SQLServerCharset.UTF8.value)
            if str(Env.get("DB_CONNECTION", "sqlite")).strip().lower() == "sqlserver"
            else SQLServerCharset.UTF8.value
        ),
        metadata={
            "description": "The charset used for the connection.",
            "default": SQLServerCharset.UTF8.value,
        },
    )

    prefix: str = field(
        default_factory=lambda: Env.get("DB_PREFIX", ""),
        metadata={
            "description": "Prefix for table names.",
            "default": "",
        },
    )

    prefix_indexes: bool = field(
        default_factory=lambda: Env.get("DB_PREFIX_INDEXES", True),
        metadata={
            "description": "Whether to prefix index names.",
            "default": True,
        },
    )

    encrypt: bool | str = field(
        default_factory=lambda: Env.get("DB_ENCRYPT", "yes"),
        metadata={
            "description": "Whether the connection must be encrypted.",
            "default": "yes",
        },
    )

    trust_server_certificate: bool = field(
        default_factory=lambda: Env.get("DB_TRUST_SERVER_CERTIFICATE", True),
        metadata={
            "description": "Whether to trust the server certificate.",
            "default": True,
        },
    )

    odbc_driver: str = field(
        default_factory=lambda: Env.get(
            "DB_ODBC_DRIVER",
            "ODBC Driver 18 for SQL Server",
        ),
        metadata={
            "description": "Name of the ODBC driver used by the connection.",
            "default": "ODBC Driver 18 for SQL Server",
        },
    )

    def __post_init__(self) -> None:
        """Validate the SQL Server configuration after initialization.

        Returns
        -------
        None
            This method validates the entity without returning a value.

        Raises
        ------
        ValueError
            If a configuration value is invalid.
        TypeError
            If a configuration field has an incorrect type.
        """
        # Validate settings in the order required by connection setup.
        super().__post_init__()
        self.__validateDriver()
        self.__validateEndpoint()
        self.__validateCredentials()
        self.__validateOptions()

    def __validateDriver(self) -> None:
        """Require the SQL Server driver discriminator.

        Returns
        -------
        None
            This method validates the driver without returning a value.

        Raises
        ------
        ValueError
            If the driver is not ``sqlserver``.
        """
        # Reject configurations that select a different database backend.
        if self.driver != "sqlserver":
            error_msg = (
                "Invalid driver: expected 'sqlserver'. Please ensure the "
                "'driver' attribute is set to 'sqlserver'."
            )
            raise ValueError(error_msg)

    def __validateEndpoint(self) -> None:
        """Validate the host, port, and database fields.

        Returns
        -------
        None
            This method validates the endpoint without returning a value.

        Raises
        ------
        ValueError
            If the host, port, or database value is invalid.
        TypeError
            If the port is not an integer.
        """
        # Keep malformed endpoint values from reaching connection setup.
        if not isinstance(self.host, str) or not self.host.strip():
            error_msg = "Database host must be a non-empty string."
            raise ValueError(error_msg)

        if not isinstance(self.port, int) or isinstance(self.port, bool):
            error_msg = "Database port must be an integer."
            raise TypeError(error_msg)
        if self.port < 1 or self.port > _MAX_PORT:
            error_msg = f"Database port must be between 1 and {_MAX_PORT}."
            raise ValueError(error_msg)

        if not isinstance(self.database, str) or not self.database.strip():
            error_msg = "Database name must be a non-empty string."
            raise ValueError(error_msg)

    def __validateCredentials(self) -> None:
        """Validate the username and password fields.

        Returns
        -------
        None
            This method validates credentials without returning a value.

        Raises
        ------
        TypeError
            If the username or password has an incorrect type.
        ValueError
            If the username is empty.
        """
        # Require a username while permitting an empty password.
        if not isinstance(self.username, str) or not self.username.strip():
            error_msg = "Database username must be a non-empty string."
            raise ValueError(error_msg)
        if not isinstance(self.password, str):
            error_msg = "Database password must be a string."
            raise TypeError(error_msg)

    def __validateOptions(self) -> None:
        """Validate the prefix, charset, and ODBC connection options.

        Returns
        -------
        None
            This method validates options without returning a value.

        Raises
        ------
        ValueError
            If an option value is invalid.
        TypeError
            If an option has an incorrect type.
        """
        # Validate options before the connection configuration is consumed.
        if not isinstance(self.prefix, str):
            error_msg = "Table prefix must be a string."
            raise TypeError(error_msg)
        if not isinstance(self.odbc_driver, str) or not self.odbc_driver.strip():
            error_msg = "The ODBC driver name must be a non-empty string."
            raise ValueError(error_msg)

        object.__setattr__(
            self,
            "charset",
            normalize_enum(self.charset, SQLServerCharset, "charset"),
        )
        validate_boolean(self.prefix_indexes, "prefix_indexes")
        validate_boolean(self.trust_server_certificate, "trust_server_certificate")
        if not isinstance(self.encrypt, (bool, str)):
            error_msg = "'encrypt' must be a boolean or a supported encryption mode."
            raise TypeError(error_msg)
        if isinstance(self.encrypt, str) and self.encrypt.strip().lower() not in {
            "yes",
            "no",
            "true",
            "false",
            "on",
            "off",
            "1",
            "0",
        }:
            error_msg = "'encrypt' is not a supported encryption mode."
            raise ValueError(error_msg)
