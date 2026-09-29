from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class RememberAuth(BaseEntity):
    """
    Configure the optional persistent login cookie separately from sessions.

    Attributes
    ----------
    cookie : str
        Name of the persistent login cookie.
    lifetime : int
        Lifetime of the persistent login cookie, in minutes.
    secure : bool
        Whether the persistent login cookie requires a secure connection.
    """

    cookie: str = field(
        default_factory=lambda: Env.get("AUTH_REMEMBER_COOKIE", "orionis_remember"),
        metadata={
            "description": "Name of the persistent login cookie.",
            "default": "orionis_remember",
        },
    )

    lifetime: int = field(
        default_factory=lambda: Env.get("AUTH_REMEMBER_LIFETIME", 43200),
        metadata={
            "description": "Lifetime of the persistent login cookie, in minutes.",
            "default": 43200,
        },
    )

    secure: bool = field(
        default_factory=lambda: Env.get("AUTH_REMEMBER_SECURE", True),
        metadata={
            "description": (
                "Whether the persistent login cookie requires a secure connection."
            ),
            "default": True,
        },
    )

    # Validate cookie naming, lifetime, and transport security settings.
    def __post_init__(self) -> None:
        """Validate persistent login cookie settings.

        Returns
        -------
        None
            Completes validation without returning a value.

        Raises
        ------
        ValueError
            If the cookie name, lifetime, or prefixed-cookie security is invalid.
        TypeError
            If ``secure`` is not a boolean.
        """
        super().__post_init__()

        # Reject cookie names that contain unsupported characters.
        if (
            not isinstance(self.cookie, str)
            or not self.cookie
            or not all(
                char.isascii() and (char.isalnum() or char in "_-")
                for char in self.cookie
            )
        ):
            error_msg = "auth.remember.cookie must be a valid cookie name."
            raise ValueError(error_msg)

        # Require a strictly positive integer lifetime.
        if type(self.lifetime) is not int or self.lifetime <= 0:
            error_msg = "auth.remember.lifetime must be a positive number of minutes."
            raise ValueError(error_msg)

        # Keep the transport-security setting explicitly boolean.
        if not isinstance(self.secure, bool):
            error_msg = "auth.remember.secure must be a boolean."
            raise TypeError(error_msg)

        # Enforce HTTPS for cookies that use a browser security prefix.
        if self.cookie.startswith(("__Host-", "__Secure-")) and not self.secure:
            error_msg = "Prefixed remember cookies require HTTPS."
            raise ValueError(error_msg)
