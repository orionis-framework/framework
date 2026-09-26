from typing import ClassVar
from orionis.auth.concerns.functions import model_primary_key
from orionis.auth.contracts.authorizable import IAuthorizable

class Authorizable:
    """
    Let any Orionis model own permissions and roles.

    Authorization rows are polymorphic: they store the type of the owner
    next to its identifier, so users, teams or API clients can all be
    granted the very same permissions.

    The mixin is a plain class registered as a virtual implementation of
    :class:`IAuthorizable`, because inheriting from the ABC directly would
    clash with ``ModelMeta``, the metaclass of every Orionis model.
    """

    __slots__ = ()

    # Value stored in the ``model_type`` column. Leave it as ``None`` to
    # derive a stable dotted path from the class itself.
    AUTHORIZABLE_TYPE: ClassVar[str | None] = None

    def getAuthorizableType(self) -> str:
        """
        Return the polymorphic type stored with the identifier.

        Returns
        -------
        str
            Explicit ``AUTHORIZABLE_TYPE`` when declared, otherwise the
            dotted path of the class.
        """
        declared = self.AUTHORIZABLE_TYPE
        if declared is not None:
            return declared

        owner = type(self)
        return f"{owner.__module__}.{owner.__qualname__}"

    def getAuthorizableId(self) -> object:
        """
        Return the identifier stored in the authorization tables.

        Returns
        -------
        object
            Primary key value, or ``None`` when the model was never
            persisted.
        """
        return getattr(self, model_primary_key(self), None)

# Registered as a virtual subclass so ``isinstance`` and ``issubclass``
# work without forcing ``ABCMeta`` onto every model.
IAuthorizable.register(Authorizable)
