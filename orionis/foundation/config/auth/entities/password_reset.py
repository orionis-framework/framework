from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class PasswordReset(BaseEntity):
    """
    Represent the configuration of password reset functionality.

    Attributes
    ----------
    expiration : int
        Lifetime of the password reset link, in minutes.
    throttle : int
        Throttle delay between password reset requests for the same account, in seconds.
    table : str
        Table storing the password reset tokens.
    """

    expiration: int = field(
        default_factory=lambda: Env.get("AUTH_PASSWORD_RESET_EXPIRATION", 60),
        metadata={
            "description": "Lifetime of the password reset link, in minutes.",
            "default": 60,
        },
    )
    throttle: int = field(
        default_factory=lambda: Env.get("AUTH_PASSWORD_RESET_THROTTLE", 60),
        metadata={
            "description": (
                "Throttle delay between password reset requests for the same account, "
                "in seconds."
            ),
            "default": 60,
        },
    )
    table: str = field(
        default_factory=lambda: Env.get(
            "AUTH_PASSWORD_RESET_TABLE",
            "password_reset_tokens",
        ),
        metadata={
            "description": "Table storing the password reset tokens.",
            "default": "password_reset_tokens",
        },
    )

    # Validate password reset limits and storage configuration.
    def __post_init__(self) -> None:
        """Validate password reset limits and the token table name.

        Returns
        -------
        None
            Completes validation without returning a value.

        Raises
        ------
        ValueError
            If a limit is not positive or the table name is empty.
        """
        super().__post_init__()
        for name in ("expiration", "throttle"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                error_msg = f"auth.passwords.{name} must be a positive integer."
                raise ValueError(error_msg)
        if not isinstance(self.table, str) or not self.table.strip():
            error_msg = "auth.passwords.table must be a non-empty string."
            raise ValueError(error_msg)
