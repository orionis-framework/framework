from abc import ABC, abstractmethod

class IAuthenticatable(ABC):
    """
    Define the minimum surface an application identity must expose.

    Authentication never depends on a concrete ``User`` class. Any object
    able to answer these three questions can be authenticated by Orionis.
    """

    __slots__ = ()

    @abstractmethod
    def getAuthIdentifierName(self) -> str:
        """
        Return the attribute holding the unique identifier.

        Returns
        -------
        str
            Name of the attribute that uniquely identifies the identity.
        """

    @abstractmethod
    def getAuthIdentifier(self) -> object:
        """
        Return the value uniquely identifying this identity.

        Returns
        -------
        object
            Value persisted in the session or in an access token so the
            identity can be restored on a later request.
        """

    @abstractmethod
    def getAuthPassword(self) -> str:
        """
        Return the stored password hash of this identity.

        Returns
        -------
        str
            Encoded hash produced by the hashing module. Never a plain
            text password.
        """
