from abc import ABC, abstractmethod

class IAuthorizable(ABC):
    """Define how an identity is addressed by the authorization tables.

    Permissions and roles are attached through a polymorphic pair, so any
    model may own them without the module knowing its concrete class.
    """

    __slots__ = ()

    @abstractmethod
    def getAuthorizableType(self) -> str:
        """Return the polymorphic type stored alongside the identifier.

        Returns
        -------
        str
            Stable string identifying the owning model, persisted in the
            ``model_type`` column of the authorization pivot tables.
        """

    @abstractmethod
    def getAuthorizableId(self) -> object:
        """Return the identifier stored in the authorization pivot tables.

        Returns
        -------
        object
            Value persisted in the ``model_id`` column.
        """
