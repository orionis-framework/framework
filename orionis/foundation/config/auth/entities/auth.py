from dataclasses import dataclass, field
from orionis.environment.facade import Env
from orionis.foundation.config.auth.entities.identity import Identity
from orionis.foundation.config.auth.entities.session import SessionAuth
from orionis.foundation.config.auth.entities.tokens import Tokens
from orionis.foundation.config.auth.enums.guards import Guards
from orionis.support.entities.base import BaseEntity

# Pre-computed frozenset of valid guard names for O(1) membership checks
_GUARD_NAMES: frozenset[str] = frozenset(Guards._member_names_)

@dataclass(frozen=True, kw_only=True)
class Auth(BaseEntity):
    """
    Represent the authentication and authorization configuration.

    Attributes
    ----------
    default : Guards | str
        Guard used when a middleware or a facade call does not name one.
        Accepts a ``Guards`` member or a plain string.
    identity : Identity | dict
        Where the application identity lives and how it is verified.
    session : SessionAuth | dict
        Options of the session guard used by web routes.
    tokens : Tokens | dict
        Options of the personal access token guard used by API routes.
    """

    default: Guards | str = field(
        default_factory=lambda: Env.get("AUTH_GUARD", Guards.SESSION.value),
        metadata={
            "description": "Guard used when no explicit guard is named.",
            "default": Guards.SESSION.value,
        },
    )

    identity: Identity | dict = field(
        default_factory=Identity,
        metadata={
            "description": (
                "Where the application identity lives and how it is "
                "verified."
            ),
        },
    )

    session: SessionAuth | dict = field(
        default_factory=SessionAuth,
        metadata={"description": "Options of the session guard."},
    )

    tokens: Tokens | dict = field(
        default_factory=Tokens,
        metadata={"description": "Options of the personal access token guard."},
    )

    def __post_init__(self) -> None:
        """
        Validate and normalize the authentication configuration.

        Returns
        -------
        None
            This method validates and normalizes attributes in place.

        Raises
        ------
        TypeError
            If an option has an unexpected type.
        ValueError
            If the default guard is not one of the supported guards.
        """
        super().__post_init__()

        # Reject types that are neither Guards enum nor string
        if not isinstance(self.default, (Guards, str)):
            error_msg = (
                "The default authentication guard must be an instance of "
                "Guards or a string."
            )
            raise TypeError(error_msg)

        # Validate string guard names and normalise to canonical enum value
        if isinstance(self.default, str):
            _value = self.default.upper().strip()
            if _value not in _GUARD_NAMES:
                error_msg = (
                    f"Invalid authentication guard: {self.default}. "
                    f"Must be one of {sorted(_GUARD_NAMES)!s}."
                )
                raise ValueError(error_msg)
            object.__setattr__(self, "default", Guards[_value].value)
        else:
            object.__setattr__(self, "default", self.default.value)

        # Convert plain dictionaries into typed configuration entities
        self.__normalizeSection("identity", Identity)
        self.__normalizeSection("session", SessionAuth)
        self.__normalizeSection("tokens", Tokens)

    def __normalizeSection(self, name: str, entity: type) -> None:
        """
        Coerce a configuration section into its typed entity.

        Parameters
        ----------
        name : str
            Name of the attribute holding the section.
        entity : type
            Entity class the section must end up being an instance of.

        Returns
        -------
        None
            The attribute is replaced in place when a dictionary is given.

        Raises
        ------
        TypeError
            If the section is neither the entity nor a dictionary.
        """
        value = getattr(self, name)
        if not isinstance(value, (entity, dict)):
            error_msg = (
                f"The auth '{name}' configuration must be an instance of "
                f"{entity.__name__} or a dictionary."
            )
            raise TypeError(error_msg)
        if isinstance(value, dict):
            object.__setattr__(self, name, entity(**value))
