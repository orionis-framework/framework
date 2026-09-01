from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Smtp(BaseEntity):
    """
    Represent SMTP configuration settings.

    Parameters
    ----------
    driver : str, default="smtp"
        The driver type for the mail transport. Default is "smtp".
    url : str
        Full URL for the SMTP service. Default is from 'MAIL_URL'.
    host : str
        Hostname of the SMTP server. Default is from 'MAIL_HOST'.
    port : int
        Port number for SMTP communication. Default is from 'MAIL_PORT' or 587.
    encryption : str
        Encryption type for secure communication. Default is from 'MAIL_ENCRYPTION'
        or 'TLS'.
    username : str
        Username for SMTP authentication. Default is from 'MAIL_USERNAME'.
    password : str
        Password for SMTP authentication. Default is from 'MAIL_PASSWORD'.
    timeout : int | None, default=None
        Connection timeout in seconds. Default is None.

    Raises
    ------
    TypeError
        If any attribute does not meet type or value requirements.
    """

    # ruff: noqa: C901

    driver : str = field(
        default="smtp",
        metadata={
            "description": "The driver type for the mail transport.",
            "default": "smtp",
        },
    )

    url: str = field(
        default_factory=lambda: Env.get("MAIL_URL", ""),
        metadata={
            "description": "The full URL for the SMTP service.",
            "default": Env.get("MAIL_URL"),
        },
    )

    host: str = field(
        default_factory=lambda: Env.get("MAIL_HOST", ""),
        metadata={
            "description": "The hostname of the SMTP server.",
            "default": Env.get("MAIL_HOST", ""),
        },
    )

    port: int = field(
        default_factory=lambda: Env.get("MAIL_PORT", 587),
        metadata={
            "description": "The port number used for SMTP communication.",
            "default": Env.get("MAIL_PORT", 587),
        },
    )

    encryption: str = field(
        default_factory=lambda: Env.get("MAIL_ENCRYPTION", "TLS"),
        metadata={
            "description": "The encryption type used for secure communication.",
            "default": Env.get("MAIL_ENCRYPTION", "TLS"),
        },
    )

    username: str = field(
        default_factory=lambda: Env.get("MAIL_USERNAME", ""),
        metadata={
            "description": "The username for authentication with the SMTP server.",
            "default": Env.get("MAIL_USERNAME"),
        },
    )

    password: str = field(
        default_factory=lambda: Env.get("MAIL_PASSWORD", ""),
        metadata={
            "description": "The password for authentication with the SMTP server.",
            "default": Env.get("MAIL_PASSWORD"),
        },
    )

    timeout: int | None = field(
        default=None,
        metadata={
            "description": "The connection timeout duration in seconds.",
            "default": None,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate initialization of SMTP configuration attributes.

        Parameters
        ----------
        None

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        TypeError
            If any attribute is not of the expected type.
        ValueError
            If any attribute has an invalid value.
        """
        # Validate 'url' type
        if not isinstance(self.url, str):
            error_msg = "The 'url' attribute must be a string."
            raise TypeError(error_msg)
        # Validate 'host' type
        if not isinstance(self.host, str):
            error_msg = "The 'host' attribute must be a string."
            raise TypeError(error_msg)
        # Validate 'port' type and value
        if not isinstance(self.port, int):
            error_msg = "The 'port' attribute must be an integer."
            raise TypeError(error_msg)
        if self.port < 0:
            error_msg = "The 'port' attribute must be a non-negative integer."
            raise ValueError(error_msg)
        # Validate 'encryption' type
        if not isinstance(self.encryption, str):
            error_msg = "The 'encryption' attribute must be a string."
            raise TypeError(error_msg)
        # Validate 'username' type
        if not isinstance(self.username, str):
            error_msg = "The 'username' attribute must be a string."
            raise TypeError(error_msg)
        # Validate 'password' type
        if not isinstance(self.password, str):
            error_msg = "The 'password' attribute must be a string."
            raise TypeError(error_msg)
        # Validate 'timeout' type and value if not None
        if self.timeout is not None:
            if not isinstance(self.timeout, int):
                error_msg = (
                    "The 'timeout' attribute must be an integer or None."
                )
                raise TypeError(error_msg)
            if self.timeout < 0:
                error_msg = (
                    "The 'timeout' attribute must be a non-negative integer or None."
                )
                raise ValueError(error_msg)
