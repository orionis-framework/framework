from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.database.enums import OracleEncoding, OracleNencoding
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Oracle(BaseEntity):
    """
    Represent Oracle database configuration for oracledb.

    Attributes
    ----------
    driver : str
        The database driver being used, typically 'oracle'.
    username : str
        Username for the database connection.
    password : str
        Password for the database connection.
    host : str
        Hostname or IP address of the Oracle server.
    port : int
        Port number for the Oracle listener (default 1521).
    service_name : str | None
        Service name for connection using the SERVICE_NAME method.
    sid : str | None
        SID for connection using the SID method.
    dsn : str | None
        Full DSN string, used if service_name/sid are not specified.
    tns_name : str | None
        TNS alias name defined in tnsnames.ora.
    encoding : str | OracleEncoding
        Character encoding for the connection.
    nencoding : str | OracleNencoding
        National character encoding for the connection.
    """

    driver: str = field(
        default="oracle",
        metadata={
            "description": "The database driver being used, typically 'oracle'.",
            "default": "oracle",
        },
    )

    username: str = field(
        default_factory=lambda: Env.get("DB_USERNAME", "sys"),
        metadata={
            "description": "Oracle DB username.",
            "default": "sys",
        },
    )

    password: str = field(
        default_factory=lambda: Env.get("DB_PASSWORD", ""),
        metadata={
            "description": "Oracle DB password.",
            "default": "",
        },
    )

    host: str = field(
        default_factory=lambda: Env.get("DB_HOST", "localhost"),
        metadata={
            "description": "Oracle DB host address.",
            "default": "localhost",
        },
    )

    port: int = field(
        default_factory=lambda: Env.get("DB_PORT", 1521),
        metadata={
            "description": "Oracle DB listener port.",
            "default": 1521,
        },
    )

    service_name: str | None = field(
        default_factory=lambda: Env.get("DB_SERVICE_NAME", "ORCL"),
        metadata={
            "description": "Service name for Oracle DB.",
            "default": "ORCL",
        },
    )

    sid: str | None = field(
        default_factory=lambda: Env.get("DB_SID", None),
        metadata={
            "description": "SID for Oracle DB.",
            "default": None,
        },
    )

    dsn: str | None = field(
        default_factory=lambda: Env.get("DB_DSN", None),
        metadata={
            "description": "DSN string (overrides host/port/service/sid).",
            "default": None,
        },
    )

    tns_name: str | None = field(
        default_factory=lambda: Env.get("DB_TNS", None),
        metadata={
            "description": "TNS alias defined in tnsnames.ora file.",
            "default": None,
        },
    )

    encoding: str | OracleEncoding = field(
        default_factory=lambda: Env.get(
            "DB_ENCODING", OracleEncoding.AL32UTF8.value,
        ),
        metadata={
            "description": "Database charset (CHAR/VARCHAR2)",
            "default": OracleEncoding.AL32UTF8.value,
        },
    )

    nencoding: str | OracleNencoding = field(
        default_factory=lambda: Env.get(
            "DB_NENCODING", OracleNencoding.AL32UTF8.value,
        ),
        metadata={
            "description": "Database charset (NCHAR/NVARCHAR2)",
            "default": OracleNencoding.AL32UTF8.value,
        },
    )

    def __validateConnectionParameters(self) -> None:
        """
        Validate Oracle connection parameters.

        Validates host, port, service_name, and sid fields when DSN and TNS are
        not provided. Ensures all required fields are present and correctly
        formatted.

        Parameters
        ----------
        self : Oracle
            The Oracle configuration instance.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If any configuration parameter is invalid.
        """
        # Validate host
        if not isinstance(self.host, str) or not self.host.strip():
            error_msg = "Invalid 'host': must be a non-empty string."
            raise ValueError(error_msg)

        # Validate port
        max_port = 65535
        if not isinstance(self.port, int) or self.port <= 0 or self.port > max_port:
            error_msg = f"Invalid 'port': must be an integer between 1 and {max_port}."
            raise ValueError(error_msg)

        # Ensure at least one of service_name or sid is provided
        if (
            self.service_name is None or not str(self.service_name).strip()
        ) and (
            self.sid is None or not str(self.sid).strip()
        ):
            error_msg = (
                "You must provide at least one of: 'service_name', 'sid', "
                "'dsn', or 'tns_name'."
            )
            raise ValueError(error_msg)

        # Validate service_name if provided
        if (
            self.service_name is not None
            and (
                not isinstance(self.service_name, str)
                or not self.service_name.strip()
            )
        ):
            error_msg = "Invalid 'service_name': must be a non-empty string or None."
            raise ValueError(error_msg)

        # Validate sid if provided
        if (
            self.sid is not None
            and (not isinstance(self.sid, str) or not self.sid.strip())
        ):
            error_msg = "Invalid 'sid': must be a non-empty string or None."
            raise ValueError(error_msg)

    def __validateEncoding(self) -> None:
        """
        Validate Oracle encoding parameters.

        Validates the `encoding` and `nencoding` fields to ensure they are valid
        OracleEncoding and OracleNencoding values.

        Parameters
        ----------
        self : Oracle
            The Oracle configuration instance.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If any encoding parameter is invalid.
        TypeError
            If any encoding parameter has an incorrect type.
        """
        # Validate encoding value and type
        options_encoding = OracleEncoding._member_names_
        if isinstance(self.encoding, str):
            _value = self.encoding.upper().strip()
            if _value not in options_encoding:
                error_msg = (
                    f"The 'encoding' attribute must be a valid option "
                    f"{OracleEncoding._member_names_!s}"
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "encoding", OracleEncoding[_value].value)
        elif isinstance(self.encoding, OracleEncoding):
            object.__setattr__(self, "encoding", self.encoding.value)
        else:
            error_msg = (
                "Invalid 'encoding': must be a string or OracleEncoding."
            )
            raise TypeError(error_msg)

    def __validateNencoding(self) -> None:
        """
        Validate the Oracle national encoding parameter.

        Validates the `nencoding` field to ensure it is a valid
        OracleNencoding value.

        Parameters
        ----------
        self : Oracle
            The Oracle configuration instance.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If the nencoding parameter is invalid.
        TypeError
            If the nencoding parameter has an incorrect type.
        """
        # Validate nencoding value and type
        options_nencoding = OracleNencoding._member_names_
        if isinstance(self.nencoding, str):
            # Normalize and check nencoding value
            _value = self.nencoding.upper().strip()
            if _value not in options_nencoding:
                error_msg = (
                    f"The 'nencoding' attribute must be a valid option "
                    f"{OracleNencoding._member_names_!s}"
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "nencoding", OracleNencoding[_value].value)
        elif isinstance(self.nencoding, OracleNencoding):
            object.__setattr__(self, "nencoding", self.nencoding.value)
        else:
            error_msg = (
                "Invalid 'nencoding': must be a string or OracleNencoding."
            )
            raise TypeError(error_msg)

    def __post_init__(self) -> None:
        """
        Validate Oracle database connection configuration after initialization.

        This method performs strict validation on the configuration fields required
        to establish an Oracle database connection. It ensures that all necessary
        parameters are present and correctly formatted, raising an appropriate
        exception if any validation fails.

        Parameters
        ----------
        self : Oracle
            The Oracle configuration instance.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If any configuration parameter is invalid.
        TypeError
            If any configuration parameter has an incorrect type.
        """
        super().__post_init__()

        # Validate driver
        if not isinstance(self.driver, str) or self.driver.strip().lower() != "oracle":
            error_msg = "Invalid 'driver': must be the string 'oracle'."
            raise ValueError(error_msg)

        # Validate username
        if not isinstance(self.username, str) or not self.username.strip():
            error_msg = "Invalid 'username': must be a non-empty string."
            raise ValueError(error_msg)

        # Validate password
        if not isinstance(self.password, str):
            error_msg = "Invalid 'password': must be a string."
            raise TypeError(error_msg)

        # Validate dsn
        if self.dsn is not None and (
            not isinstance(self.dsn, str) or not self.dsn.strip()
        ):
            error_msg = "Invalid 'dsn': must be a non-empty string or None."
            raise ValueError(error_msg)

        # Validate tns_name
        if self.tns_name is not None and (
            not isinstance(self.tns_name, str) or not self.tns_name.strip()
        ):
            error_msg = (
                "Invalid 'tns_name': must be a non-empty string or None."
            )
            raise ValueError(error_msg)

        # If not using DSN or TNS, validate host/port/service_name/sid
        if not self.dsn and not self.tns_name:
            self.__validateConnectionParameters()

        # Validate encoding
        self.__validateEncoding()

        # Validate nencoding
        self.__validateNencoding()
