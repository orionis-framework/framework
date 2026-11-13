# ruff: noqa: S105
# AUTH_PASSWORD names an attribute and does not contain a credential.

"""Turn any Orionis model into an authenticatable identity."""

from typing import ClassVar
from orionis.auth.concerns.functions import model_primary_key
from orionis.auth.contracts.authenticatable import IAuthenticatable


class Authenticatable:
    """
    Turn any Orionis model into an authenticatable identity.

    Mix it into the model backing application identities.

    The mixin is a plain class registered as a virtual implementation of
    :class:`orionis.auth.contracts.IAuthenticatable`. Inheriting from the ABC directly
    would
    clash with ``ModelMeta``, the metaclass of every Orionis model.
    """

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    # Attribute holding the password hash. Override it when the model
    # stores the hash under a different name.
    AUTH_PASSWORD: ClassVar[str] = "password"
    """
    Attribute holding the password hash. Override it when the model stores the hash
    under a different name.
    """

    def getAuthIdentifierName(self) -> str:
        """
        Return the attribute holding the unique identifier.

        Returns
        -------
        str
            Primary key declared by the model metadata.
        """
        return model_primary_key(self)

    def getAuthIdentifier(self) -> object:
        """
        Return the value uniquely identifying this identity.

        Returns
        -------
        object
            Primary key value, or ``None`` when the model was never
            persisted.
        """
        return getattr(self, model_primary_key(self), None)

    def getAuthPassword(self) -> str:
        """
        Return the stored password hash of this identity.

        Returns
        -------
        str
            Encoded hash, or an empty string when the attribute is unset.
        """
        stored = getattr(self, self.AUTH_PASSWORD, None)
        return stored if isinstance(stored, str) else ""


# Registered as a virtual subclass so ``isinstance`` and ``issubclass``
# work without forcing ``ABCMeta`` onto every model.
IAuthenticatable.register(Authenticatable)
