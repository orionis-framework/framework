from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.validation import validate_string
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
        If any attribute does not meet its structural type requirements.
    """

    driver: str = field(
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
            "default": "",
        },
    )

    host: str = field(
        default_factory=lambda: Env.get("MAIL_HOST", ""),
        metadata={
            "description": "The hostname of the SMTP server.",
            "default": "",
        },
    )

    port: int = field(
        default_factory=lambda: Env.get("MAIL_PORT", 587),
        metadata={
            "description": "The port number used for SMTP communication.",
            "default": 587,
        },
    )

    encryption: str = field(
        default_factory=lambda: Env.get("MAIL_ENCRYPTION", "TLS"),
        metadata={
            "description": "The encryption type used for secure communication.",
            "default": "TLS",
        },
    )

    username: str = field(
        default_factory=lambda: Env.get("MAIL_USERNAME", ""),
        metadata={
            "description": "The username for authentication with the SMTP server.",
            "default": "",
        },
    )

    password: str = field(
        default_factory=lambda: Env.get("MAIL_PASSWORD", ""),
        metadata={
            "description": "The password for authentication with the SMTP server.",
            "default": "",
        },
    )

    timeout: int | None = field(
        default_factory=lambda: Env.get("MAIL_TIMEOUT", None),
        metadata={
            "description": "The connection timeout duration in seconds.",
            "default": None,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the structural types of the SMTP settings.

        This method ensures that the 'driver' is set to 'smtp' and that all other
        attributes conform to their expected types. It allows 'timeout' to be None.

        Raises
        ------
        TypeError
            If any attribute does not meet its structural type requirements.
        """
        super().__post_init__()
        if self.driver != "smtp":
            message = "The 'driver' attribute must be 'smtp'."
            raise TypeError(message)
        for name in ("url", "host", "encryption", "username", "password"):
            validate_string(getattr(self, name), name, allow_empty=True)
        for name in ("port", "timeout"):
            value = getattr(self, name)
            if name == "timeout" and value is None:
                continue
            if not isinstance(value, int) or isinstance(value, bool):
                message = f"'{name}' must be an integer."
                raise TypeError(message)
