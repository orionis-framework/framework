from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Identity(BaseEntity):
    """
    Represent how the application identity is located and verified.

    The framework never imports the identity class directly: it receives
    a dotted path and resolves it lazily, so any model may play the role
    of the authenticatable identity.

    Attributes
    ----------
    model : str
        Dotted path of the model backing the authenticated identity.
    username : str
        Attribute holding the public credential used to look an identity
        up, such as the email address.
    """

    model: str = field(
        default_factory=lambda: Env.get("AUTH_MODEL", "app.models.user.User"),
        metadata={
            "description": (
                "Dotted path of the model backing the authenticated identity."
            ),
            "default": "app.models.user.User",
        },
    )

    username: str = field(
        default_factory=lambda: Env.get("AUTH_USERNAME", "email"),
        metadata={
            "description": (
                "Attribute used to look an identity up from the submitted credentials."
            ),
            "default": "email",
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the identity configuration after initialization.

        Returns
        -------
        None
            This method validates the instance attributes in place.

        Raises
        ------
        TypeError
            If any option is not a string.
        ValueError
            If the model path does not look like a dotted class path.
        """
        super().__post_init__()

        # Every option identifies an attribute or a class, so all of them
        # must be plain non-empty strings.
        for name in ("model", "username"):
            value = getattr(self, name)
            if not isinstance(value, str):
                error_msg = f"The auth identity '{name}' option must be a string."
                raise TypeError(error_msg)
            if not value.strip():
                error_msg = f"The auth identity '{name}' option cannot be empty."
                raise ValueError(error_msg)

        # A dotted path is required to split the module from the class.
        if "." not in self.model or not all(
            part.isidentifier() for part in self.model.split(".")
        ):
            error_msg = (
                "The auth identity 'model' option must be a dotted path "
                "such as 'app.models.user.User'."
            )
            raise ValueError(error_msg)
