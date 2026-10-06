from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.database.enums.redshift_mode import RedshiftSSLMode
from orionis.foundation.config.validation import (
    normalize_enum, validate_boolean, validate_integer, validate_string,
)
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Redshift(BaseEntity):
    """
    Configure Amazon Redshift with the official AWS Python connector.

    Attributes
    ----------
    driver : str
        Fixed Redshift driver identifier.
    host : str | None
        Cluster endpoint, or None when IAM resolves the endpoint.
    port : str | int
        Database port, defaulting to 5439.
    database : str
        Database name.
    username : str | None
        Database authentication user.
    password : str | None
        Database authentication password, unused with IAM credentials.
    prefix : str
        Table name prefix.
    ssl : bool
        Enable TLS for database connections.
    sslmode : str | RedshiftSSLMode
        Certificate verification policy, defaulting to verify-full.
    timeout : int | None
        Connection socket timeout in seconds, or None for no timeout.
    iam : bool
        Enable the connector's IAM authentication.
    region : str | None
        AWS region used for IAM endpoint and credential resolution.
    cluster_identifier : str | None
        Provisioned cluster identifier for IAM authentication.
    db_user : str | None
        Database user requested through IAM.
    profile : str | None
        AWS credentials profile; None uses the SDK credential chain.
    is_serverless : bool
        Select Redshift Serverless instead of a provisioned cluster.
    serverless_work_group : str | None
        Serverless workgroup used for endpoint resolution.
    serverless_acct_id : str | None
        AWS account owning the Serverless workgroup.
    """

    driver: str = field(
        default="redshift",
        metadata={"description": "Database driver type", "default": "redshift"},
    )

    host: str | None = field(
        default_factory=lambda: Env.get("DB_HOST", "127.0.0.1"),
        metadata={"description": "Cluster endpoint", "default": "127.0.0.1"},
    )

    port: str | int = field(
        default_factory=lambda: Env.get("DB_PORT", 5439),
        metadata={"description": "Database port", "default": 5439},
    )

    database: str = field(
        default_factory=lambda: Env.get("DB_DATABASE", "dev"),
        metadata={"description": "Database name", "default": "dev"},
    )

    username: str | None = field(
        default_factory=lambda: Env.get("DB_USERNAME", "awsuser"),
        metadata={"description": "Database user", "default": "awsuser"},
    )

    password: str | None = field(
        default_factory=lambda: Env.get("DB_PASSWORD", ""),
        metadata={"description": "Database password", "default": ""},
    )

    prefix: str = field(
        default_factory=lambda: Env.get("DB_PREFIX", ""),
        metadata={"description": "Table prefix", "default": ""},
    )

    ssl: bool = field(
        default_factory=lambda: Env.get("DB_REDSHIFT_SSL", True),
        metadata={"description": "Enable TLS", "default": True},
    )

    sslmode: str | RedshiftSSLMode = field(
        default_factory=lambda: Env.get(
            "DB_REDSHIFT_SSLMODE", RedshiftSSLMode.VERIFY_FULL,
        ),
        metadata={
            "description": "Certificate verification policy",
            "default": RedshiftSSLMode.VERIFY_FULL.value,
        },
    )

    timeout: int | None = field(
        default_factory=lambda: Env.get("DB_REDSHIFT_TIMEOUT", 30),
        metadata={"description": "Socket timeout in seconds", "default": 30},
    )

    iam: bool = field(
        default_factory=lambda: Env.get("DB_REDSHIFT_IAM", False),
        metadata={"description": "Enable IAM authentication", "default": False},
    )

    region: str | None = field(
        default_factory=lambda: Env.get("DB_REDSHIFT_REGION", None),
        metadata={"description": "AWS region", "default": None},
    )

    cluster_identifier: str | None = field(
        default_factory=lambda: Env.get("DB_REDSHIFT_CLUSTER_IDENTIFIER", None),
        metadata={"description": "Provisioned cluster identifier", "default": None},
    )

    db_user: str | None = field(
        default_factory=lambda: Env.get("DB_REDSHIFT_DB_USER", None),
        metadata={"description": "IAM database user", "default": None},
    )

    profile: str | None = field(
        default_factory=lambda: Env.get("DB_REDSHIFT_PROFILE", None),
        metadata={"description": "AWS credentials profile", "default": None},
    )

    is_serverless: bool = field(
        default_factory=lambda: Env.get("DB_REDSHIFT_IS_SERVERLESS", False),
        metadata={"description": "Select Redshift Serverless", "default": False},
    )

    serverless_work_group: str | None = field(
        default_factory=lambda: Env.get("DB_REDSHIFT_SERVERLESS_WORK_GROUP", None),
        metadata={"description": "Serverless workgroup", "default": None},
    )

    serverless_acct_id: str | None = field(
        default_factory=lambda: Env.get("DB_REDSHIFT_SERVERLESS_ACCT_ID", None),
        metadata={"description": "Serverless AWS account", "default": None},
    )

    def __post_init__(self) -> None:
        """
        Validate connector settings without contacting AWS or opening a socket.

        Returns
        -------
        None
            Validate scalar fields and store the canonical SSL mode.

        Raises
        ------
        TypeError
            If a setting has an incompatible type.
        ValueError
            If the driver, port, timeout or SSL mode is invalid.
        """
        super().__post_init__()
        if self.driver != "redshift":
            message = "The 'driver' property must be 'redshift'."
            raise ValueError(message)
        validate_string(self.database, "database")
        validate_string(self.prefix, "prefix", allow_empty=True)
        for name in (
            "host", "username", "region", "cluster_identifier", "db_user",
            "profile", "serverless_work_group", "serverless_acct_id",
        ):
            value = getattr(self, name)
            if value is not None:
                validate_string(value, name)
        if self.password is not None:
            validate_string(self.password, "password", allow_empty=True)
        port = self.port
        if isinstance(port, str) and port.isascii() and port.isdecimal():
            port = int(port)
        validate_integer(port, "port", minimum=1, maximum=65535)
        if self.timeout is not None:
            validate_integer(self.timeout, "timeout", minimum=1)
        for name in ("ssl", "iam", "is_serverless"):
            validate_boolean(getattr(self, name), name)
        object.__setattr__(
            self, "sslmode", normalize_enum(self.sslmode, RedshiftSSLMode, "sslmode"),
        )
