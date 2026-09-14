from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class SessionAuth(BaseEntity):
    """
    Represent the configuration of session based authentication.

    Only the keys owned by authentication live here. Cookie lifetime,
    driver and encryption keep their single source of truth in
    ``config/session.py``.

    Attributes
    ----------
    key : str
        Session key holding the identifier of the authenticated identity.
    redirect_to : str | None
        Path browsers are redirected to when authentication is required.
        ``None`` renders the standard ``401`` error response instead.
    """

    key: str = field(
        default="_auth_identifier",
        metadata={
            "description": (
                "Session key holding the identifier of the authenticated "
                "identity."
            ),
            "default": "_auth_identifier",
        },
    )

    redirect_to: str | None = field(
        default_factory=lambda: Env.get("AUTH_REDIRECT_TO", None),
        metadata={
            "description": (
                "Path browsers are redirected to when authentication is "
                "required. Null renders the standard 401 response."
            ),
            "default": None,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the session authentication options after initialization.

        Returns
        -------
        None
            This method validates the instance attributes in place.

        Raises
        ------
        TypeError
            If ``key`` is not a string, or ``redirect_to`` is neither a
            string nor ``None``.
        ValueError
            If ``key`` is empty.
        """
        super().__post_init__()

        if not isinstance(self.key, str):
            error_msg = "The auth session 'key' option must be a string."
            raise TypeError(error_msg)
        if not self.key.strip():
            error_msg = "The auth session 'key' option cannot be empty."
            raise ValueError(error_msg)

        if self.redirect_to is not None and not isinstance(self.redirect_to, str):
            error_msg = (
                "The auth session 'redirect_to' option must be a string "
                "or null."
            )
            raise TypeError(error_msg)
