from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.database.enums import (
    MySQLCharset,
    MySQLCollation,
    MySQLEngine,
)
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class MySQL(BaseEntity):
    """
    Data class to represent the MySQL database configuration.

    Attributes
    ----------
    driver : str
        The database driver being used, e.g., 'mysql'.
    host : str
        The host address for the MySQL server.
    port : str
        The port for connecting to the MySQL server.
    database : str
        The name of the MySQL database.
    username : str
        The username for connecting to the MySQL database.
    password : str
        The password for the MySQL database.
    unix_socket : str
        The path to the Unix socket for MySQL connections (optional).
    charset : str
        The charset used for the connection.
    collation : str
        The collation for the database.
    prefix : str
        Prefix for table names.
    prefix_indexes : bool
        Whether to prefix index names.
    strict : bool
        Whether to enforce strict SQL mode.
    engine : Optional[str]
        The storage engine for the MySQL database (optional).
    """

    # ruff: noqa: C901

    driver: str = field(
        default = "mysql",
        metadata = {
            "description": "The database driver being used.",
            "default": "mysql",
        },
    )

    host: str = field(
        default_factory = lambda: Env.get("DB_HOST", "127.0.0.1"),
        metadata = {
            "description": "The host address for the MySQL server.",
            "default": "127.0.0.1",
        },
    )

    port: int = field(
        default_factory = lambda: Env.get("DB_PORT", 3306),
        metadata = {
            "description": "The port for connecting to the MySQL server.",
            "default": 3306,
        },
    )

    database: str = field(
        default_factory = lambda: Env.get("DB_DATABASE", "orionis"),
        metadata = {
            "description": "The name of the MySQL database.",
            "default": "orionis",
        },
    )

    username: str = field(
        default_factory = lambda: Env.get("DB_USERNAME", "root"),
        metadata = {
            "description": "The username for connecting to the MySQL database.",
            "default": "root",
        },
    )

    password: str = field(
        default_factory = lambda: Env.get("DB_PASSWORD", ""),
        metadata = {
            "description": "The password for the MySQL database.",
            "default": "",
        },
    )

    unix_socket: str = field(
        default_factory = lambda: Env.get("DB_SOCKET", ""),
        metadata = {
            "description": "The path to the Unix socket for MySQL connections "
                          "(optional).",
            "default": "",
        },
    )

    charset: str | MySQLCharset = field(
        default = MySQLCharset.UTF8MB4.value,
        metadata = {
            "description": "The charset used for the connection.",
            "default": MySQLCharset.UTF8MB4.value,
        },
    )

    collation: str | MySQLCollation = field(
        default = MySQLCollation.UTF8MB4_UNICODE_CI.value,
        metadata = {
            "description": "The collation for the database.",
            "default": MySQLCollation.UTF8MB4_UNICODE_CI.value,
        },
    )

    prefix: str = field(
        default = "",
        metadata = {
            "description": "Prefix for table names.",
            "default": "",
        },
    )

    prefix_indexes: bool = field(
        default = True,
        metadata = {
            "description": "Whether to prefix index names.",
            "default": True,
        },
    )

    strict: bool = field(
        default = True,
        metadata = {
            "description": "Whether to enforce strict SQL mode.",
            "default": True,
        },
    )

    engine: str | MySQLEngine = field(
        default = MySQLEngine.INNODB.value,
        metadata = {
            "description": "The storage engine for the MySQL database (optional).",
            "default": MySQLEngine.INNODB.value,
        },
    )

    def __post_init__(self) -> None:  # NOSONAR
        """
        Perform post-initialization validation for MySQL configuration.

        Validates all required fields for type and value correctness. Raises
        descriptive exceptions if any validation fails.

        Parameters
        ----------
        self : MySQL
            The instance of the MySQL configuration entity.

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

        # Validate driver
        if self.driver != "mysql":
            error_msg = (
                "Invalid driver: expected 'mysql'. Please ensure the 'driver' "
                "attribute is set to 'mysql'."
            )
            raise ValueError(error_msg)

        # Validate host
        if not self.host or not isinstance(self.host, str):
            error_msg = "Database host must be a non-empty string."
            raise ValueError(error_msg)

        # Validate port type
        if not isinstance(self.port, int):
            error_msg = "Database port must be an integer."
            raise TypeError(error_msg)

        # Validate port range
        max_port = 65535
        if self.port > max_port or self.port < 1:
            error_msg = f"Database port must be between 1 and {max_port}."
            raise ValueError(error_msg)

        # Validate database name
        if not self.database or not isinstance(self.database, str):
            error_msg = "Database name must be a non-empty string."
            raise ValueError(error_msg)

        # Validate username
        if not self.username or not isinstance(self.username, str):
            error_msg = "Database username must be a non-empty string."
            raise ValueError(error_msg)

        # Validate password
        if self.password is None or not isinstance(self.password, str):
            error_msg = (
                "Database password must be a string (can be empty for some setups)."
            )
            raise TypeError(error_msg)

        # Validate unix_socket
        if self.unix_socket is not None and not isinstance(self.unix_socket, str):
            error_msg = "Unix socket path must be a string."
            raise TypeError(error_msg)

        # Validate charset
        self.__ValidateCharset()

        # Validate collation
        self.__ValidateCollation()

        # Validate prefix
        if self.prefix is not None and not isinstance(self.prefix, str):
            error_msg = "Prefix must be a string."
            raise TypeError(error_msg)

        # Validate prefix_indexes
        if not isinstance(self.prefix_indexes, bool):
            error_msg = "prefix_indexes must be a boolean value."
            raise TypeError(error_msg)

        # Validate strict
        if not isinstance(self.strict, bool):
            error_msg = "strict must be a boolean value."
            raise TypeError(error_msg)

        # Validate engine
        self.__ValidateEngine()

    def __ValidateCharset(self) -> None:
        """
        Validate and normalize the charset attribute.

        Ensures that the charset is a non-empty string or a MySQLCharset enum.
        Converts string values to the corresponding MySQLCharset enum value.

        Parameters
        ----------
        self : MySQL
            Instance of the MySQL configuration entity.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If charset is not a string or MySQLCharset enum.
        ValueError
            If charset is not a valid MySQLCharset option.
        """
        # Ensure charset is a valid string or enum
        if not self.charset or not isinstance(self.charset, (str, MySQLCharset)):
            error_msg = (
                "Charset must be a non-empty string or MySQLCharset enum."
            )
            raise TypeError(error_msg)

        # Convert string charset to MySQLCharset enum value
        if isinstance(self.charset, str):
            _value = str(self.charset).upper().strip()
            options_charsets = MySQLCharset._member_names_
            if _value not in options_charsets:
                error_msg = (
                    f"Charset must be a valid MySQLCharset "
                    f"({options_charsets!s}) or string."
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "charset", MySQLCharset[_value].value)
        else:
            object.__setattr__(self, "charset", self.charset.value)

    def __ValidateCollation(self) -> None:
        """
        Validate and normalize the collation attribute.

        Ensure that the collation is a non-empty string or a MySQLCollation enum.
        Convert string values to the corresponding MySQLCollation enum value.

        Parameters
        ----------
        self : MySQL
            Instance of the MySQL configuration entity.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If collation is not a string or MySQLCollation enum.
        ValueError
            If collation is not a valid MySQLCollation option.
        """
        # Ensure collation is a valid string or enum
        if not self.collation or not isinstance(self.collation, (str, MySQLCollation)):
            error_msg = (
                "Collation must be a non-empty string or MySQLCollation enum."
            )
            raise TypeError(error_msg)

        # Convert string collation to MySQLCollation enum value
        if isinstance(self.collation, str):
            _value = str(self.collation).upper().strip()
            options_collations = MySQLCollation._member_names_
            if _value not in options_collations:
                error_msg = (
                    f"Collation must be a valid MySQLCollation "
                    f"({options_collations!s}) or string."
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "collation", MySQLCollation[_value].value)
        else:
            object.__setattr__(self, "collation", self.collation.value)

    def __ValidateEngine(self) -> None:
        """
        Validate and normalize the engine attribute.

        Parameters
        ----------
        self : MySQL
            Instance of the MySQL configuration entity.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If engine is not a string or MySQLEngine enum.
        ValueError
            If engine is not a valid MySQLEngine option.
        """
        # Validate engine type and value
        if self.engine is not None:
            # Check if engine is a string or MySQLEngine enum
            if not isinstance(self.engine, (str, MySQLEngine)):
                error_msg = "Engine must be a string or MySQLEngine enum."
                raise TypeError(error_msg)

            # Convert engine to MySQLEngine enum if it's a string
            options_engines = MySQLEngine._member_names_
            if isinstance(self.engine, str):
                _value = str(self.engine).upper().strip()
                if _value not in options_engines:
                    error_msg = (
                        f"Engine must be a valid MySQLEngine "
                        f"({options_engines!s}) or string."
                    )
                    raise ValueError(error_msg)
                object.__setattr__(self, "engine", MySQLEngine[_value].value)
            elif isinstance(self.engine, MySQLEngine):
                object.__setattr__(self, "engine", self.engine.value)
