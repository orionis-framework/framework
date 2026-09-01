from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
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

    charset: str = field(
        default_factory=lambda: Env.get("DB_CHARSET", "utf8"),
        metadata={
            "description": "The charset used for the connection.",
            "default": "utf8",
        },
    )

    prefix: str = field(
        default="",
        metadata={
            "description": "Prefix for table names.",
            "default": "",
        },
    )

    prefix_indexes: bool = field(
        default=True,
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
            "DB_ODBC_DRIVER", "ODBC Driver 18 for SQL Server",
        ),
        metadata={
            "description": "Name of the ODBC driver used by the connection.",
            "default": "ODBC Driver 18 for SQL Server",
        },
    )

    def __post_init__(self) -> None:
        """
        Perform post-initialization validation for the configuration.

        Validates connection endpoint, credentials, and driver options,
        raising descriptive exceptions when any value is invalid.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If any attribute has an invalid value.
        TypeError
            If any attribute has an incorrect type.
        """
        super().__post_init__()
        self.__validateDriver()
        self.__validateEndpoint()
        self.__validateCredentials()
        self.__validateOptions()

    def __validateDriver(self) -> None:
        """
        Validate the driver discriminator field.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the driver is not 'sqlserver'.
        """
        if self.driver != "sqlserver":
            error_msg = (
                "Invalid driver: expected 'sqlserver'. Please ensure the "
                "'driver' attribute is set to 'sqlserver'."
            )
            raise ValueError(error_msg)

    def __validateEndpoint(self) -> None:
        """
        Validate host, port, and database fields.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the host, port, or database are invalid.
        TypeError
            If the port is not an integer.
        """
        if not self.host or not isinstance(self.host, str):
            error_msg = "Database host must be a non-empty string."
            raise ValueError(error_msg)

        if not isinstance(self.port, int):
            error_msg = "Database port must be an integer."
            raise TypeError(error_msg)
        if self.port < 1 or self.port > _MAX_PORT:
            error_msg = f"Database port must be between 1 and {_MAX_PORT}."
            raise ValueError(error_msg)

        if not self.database or not isinstance(self.database, str):
            error_msg = "Database name must be a non-empty string."
            raise ValueError(error_msg)

    def __validateCredentials(self) -> None:
        """
        Validate username and password fields.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If the username or password have an incorrect type.
        ValueError
            If the username is empty.
        """
        if not self.username or not isinstance(self.username, str):
            error_msg = "Database username must be a non-empty string."
            raise ValueError(error_msg)
        if not isinstance(self.password, str):
            error_msg = "Database password must be a string."
            raise TypeError(error_msg)

    def __validateOptions(self) -> None:
        """
        Validate prefix and ODBC driver options.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the ODBC driver name is empty.
        TypeError
            If the prefix is not a string.
        """
        if not isinstance(self.prefix, str):
            error_msg = "Table prefix must be a string."
            raise TypeError(error_msg)
        if not self.odbc_driver or not isinstance(self.odbc_driver, str):
            error_msg = "The ODBC driver name must be a non-empty string."
            raise ValueError(error_msg)
