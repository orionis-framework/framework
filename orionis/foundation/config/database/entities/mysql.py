from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.foundation.config.database.enums import (
    MySQLCharset,
    MySQLCollation,
    MySQLEngine,
)
from orionis.foundation.config.validation import (
    validate_boolean,
    validate_integer,
    validate_string,
)
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

    driver: str = field(
        default="mysql",
        metadata={
            "description": "The database driver being used.",
            "default": "mysql",
        },
    )

    host: str = field(
        default_factory=lambda: Env.get("DB_HOST", "127.0.0.1"),
        metadata={
            "description": "The host address for the MySQL server.",
            "default": "127.0.0.1",
        },
    )

    port: int = field(
        default_factory=lambda: Env.get("DB_PORT", 3306),
        metadata={
            "description": "The port for connecting to the MySQL server.",
            "default": 3306,
        },
    )

    database: str = field(
        default_factory=lambda: Env.get("DB_DATABASE", "orionis"),
        metadata={
            "description": "The name of the MySQL database.",
            "default": "orionis",
        },
    )

    username: str = field(
        default_factory=lambda: Env.get("DB_USERNAME", "root"),
        metadata={
            "description": "The username for connecting to the MySQL database.",
            "default": "root",
        },
    )

    password: str = field(
        default_factory=lambda: Env.get("DB_PASSWORD", ""),
        metadata={
            "description": "The password for the MySQL database.",
            "default": "",
        },
    )

    unix_socket: str | None = field(
        default_factory=lambda: Env.get("DB_SOCKET", ""),
        metadata={
            "description": "The path to the Unix socket for MySQL connections "
            "(optional).",
            "default": "",
        },
    )

    charset: str | MySQLCharset = field(
        default_factory=lambda: (
            Env.get("DB_CHARSET", MySQLCharset.UTF8MB4.value)
            if str(Env.get("DB_CONNECTION", "sqlite")).strip().lower() == "mysql"
            else MySQLCharset.UTF8MB4.value
        ),
        metadata={
            "description": "The charset used for the connection.",
            "default": "utf8mb4",
        },
    )

    collation: str | MySQLCollation = field(
        default_factory=lambda: Env.get(
            "DB_COLLATION",
            MySQLCollation.UTF8MB4_UNICODE_CI.value,
        ),
        metadata={
            "description": "The collation for the database.",
            "default": "utf8mb4_unicode_ci",
        },
    )

    prefix: str | None = field(
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

    strict: bool = field(
        default_factory=lambda: Env.get("DB_STRICT", True),
        metadata={
            "description": "Whether to enforce strict SQL mode.",
            "default": True,
        },
    )

    engine: str | MySQLEngine | None = field(
        default_factory=lambda: Env.get("DB_ENGINE", MySQLEngine.INNODB.value),
        metadata={
            "description": "The storage engine for the MySQL database (optional).",
            "default": "InnoDB",
        },
    )

    def __post_init__(self) -> None:
        """
        Validate connection settings and normalize MySQL options.

        Parameters
        ----------
        self : MySQL
            Instance of the MySQL configuration entity.

        Returns
        -------
        None
            This method validates the entity in place and returns no value.

        Raises
        ------
        TypeError
            If a setting has an invalid type.
        ValueError
            If a setting has an invalid value.
        """
        # Validate inherited entity fields before checking MySQL-specific options.
        super().__post_init__()
        if self.driver != "mysql":
            error_msg = "The 'driver' property must be 'mysql'."
            raise ValueError(error_msg)
        for name in ("host", "database", "username"):
            validate_string(getattr(self, name), name)
        validate_integer(self.port, "port", minimum=1, maximum=65535)
        validate_string(self.password, "password", allow_empty=True)
        for name in ("unix_socket", "prefix"):
            value = getattr(self, name)
            if value is not None:
                validate_string(value, name, allow_empty=True)
        validate_boolean(self.prefix_indexes, "prefix_indexes")
        validate_boolean(self.strict, "strict")
        self.__validateCharset()
        self.__validateCollation()
        self.__validateEngine()

    def __validateCharset(self) -> None:
        """
        Validate and normalize the MySQL charset.

        Accept a non-empty string or a ``MySQLCharset`` member and store the
        corresponding canonical enum value.

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
        # Ensure the charset is a valid string or enum member.
        if not self.charset or not isinstance(self.charset, (str, MySQLCharset)):
            error_msg = "Charset must be a non-empty string or MySQLCharset enum."
            raise TypeError(error_msg)

        # Convert string input to the canonical enum value.
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

    def __validateCollation(self) -> None:
        """
        Validate and normalize the MySQL collation.

        Accept a non-empty string or a ``MySQLCollation`` member and store the
        corresponding canonical enum value.

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
        # Ensure the collation is a valid string or enum member.
        if not self.collation or not isinstance(self.collation, (str, MySQLCollation)):
            error_msg = "Collation must be a non-empty string or MySQLCollation enum."
            raise TypeError(error_msg)

        # Convert string input to the canonical enum value.
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

    def __validateEngine(self) -> None:
        """
        Validate and normalize the MySQL storage engine.

        Accept a string or ``MySQLEngine`` member and store the corresponding
        canonical enum value when an engine is configured.

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
        # Validate and normalize the optional engine setting.
        if self.engine is not None:
            # Check whether the engine is a string or enum member.
            if not isinstance(self.engine, (str, MySQLEngine)):
                error_msg = "Engine must be a string or MySQLEngine enum."
                raise TypeError(error_msg)

            # Convert string input to the canonical enum value.
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
