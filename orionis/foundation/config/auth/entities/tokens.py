from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

# Number of random bytes used to build the secret half of a token.
_MIN_SECRET_BYTES: int = 32
_MAX_SECRET_BYTES: int = 128

@dataclass(frozen=True, kw_only=True)
class Tokens(BaseEntity):
    """
    Represent the configuration of personal access token authentication.

    Attributes
    ----------
    table : str
        Table storing the issued personal access tokens.
    expiration : int | None
        Lifetime of a freshly issued token, in minutes. ``None`` issues
        tokens that never expire on their own.
    secret_bytes : int
        Number of random bytes used to build the secret of a token.
    """

    table: str = field(
        default="personal_access_tokens",
        metadata={
            "description": "Table storing the issued personal access tokens.",
            "default": "personal_access_tokens",
        },
    )

    expiration: int | None = field(
        default_factory=lambda: Env.get("AUTH_TOKEN_EXPIRATION", None),
        metadata={
            "description": (
                "Lifetime of a freshly issued token, in minutes. Null "
                "issues tokens that never expire on their own."
            ),
            "default": None,
        },
    )

    secret_bytes: int = field(
        default=40,
        metadata={
            "description": (
                "Number of random bytes used to build the secret of a "
                "token. Must be between 32 and 128."
            ),
            "default": 40,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the token configuration after initialization.

        Returns
        -------
        None
            This method validates the instance attributes in place.

        Raises
        ------
        TypeError
            If any option has an unexpected type.
        ValueError
            If ``table`` is empty, ``expiration`` is not positive, or
            ``secret_bytes`` falls outside the supported range.
        """
        super().__post_init__()

        if not isinstance(self.table, str):
            error_msg = "The auth tokens 'table' option must be a string."
            raise TypeError(error_msg)
        if not self.table.strip():
            error_msg = "The auth tokens 'table' option cannot be empty."
            raise ValueError(error_msg)

        if self.expiration is not None:
            if not isinstance(self.expiration, int) or isinstance(
                self.expiration, bool,
            ):
                error_msg = (
                    "The auth tokens 'expiration' option must be an integer "
                    "or null."
                )
                raise TypeError(error_msg)
            if self.expiration <= 0:
                error_msg = (
                    "The auth tokens 'expiration' option must be greater "
                    "than zero."
                )
                raise ValueError(error_msg)

        if not isinstance(self.secret_bytes, int) or isinstance(
            self.secret_bytes, bool,
        ):
            error_msg = "The auth tokens 'secret_bytes' option must be an integer."
            raise TypeError(error_msg)
        if not _MIN_SECRET_BYTES <= self.secret_bytes <= _MAX_SECRET_BYTES:
            error_msg = (
                f"The auth tokens 'secret_bytes' option must be between "
                f"{_MIN_SECRET_BYTES} and {_MAX_SECRET_BYTES}."
            )
            raise ValueError(error_msg)
