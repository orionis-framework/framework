from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.auth.contracts.authenticatable import IAuthenticatable
    from orionis.auth.contracts.snapshot import IAuthorizationSnapshot

class IAuthenticationContext(ABC):
    """Define the authenticated state bound to a single request.

    The context is never stored on a singleton. It lives in the container
    scope opened by the HTTP kernel, so two concurrent requests can never
    observe each other's identity.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def identity(self) -> IAuthenticatable | None:
        """Return the authenticated identity of the request.

        Returns
        -------
        IAuthenticatable | None
            Resolved identity, or ``None`` for a guest request.
        """

    @property
    @abstractmethod
    def guard(self) -> str | None:
        """Return the name of the guard that resolved the identity.

        Returns
        -------
        str | None
            Guard name, or ``None`` when nobody authenticated the request.
        """

    @property
    @abstractmethod
    def abilities(self) -> frozenset[str] | None:
        """Return the abilities carried by the presented credential.

        Returns
        -------
        frozenset[str] | None
            Abilities of the access token, or ``None`` when the credential
            does not restrict the authorization of the identity.
        """

    @property
    @abstractmethod
    def credentialId(self) -> object | None:
        """Return the identifier of the credential that authenticated.

        Returns
        -------
        object | None
            Identifier of the revocable credential, such as a personal
            access token, or ``None`` when the guard uses none.
        """

    @property
    @abstractmethod
    def isAuthenticated(self) -> bool:
        """Report whether the request carries an authenticated identity.

        Returns
        -------
        bool
            True when an identity was resolved by a guard.
        """

    @property
    @abstractmethod
    def isGuest(self) -> bool:
        """Report whether the request is anonymous.

        Returns
        -------
        bool
            True when no identity was resolved by any guard.
        """

    @abstractmethod
    def identifier(self) -> object | None:
        """Return the unique identifier of the authenticated identity.

        Returns
        -------
        object | None
            Identifier of the identity, or ``None`` for a guest request.
        """

    @abstractmethod
    async def authorization(self) -> IAuthorizationSnapshot:
        """Return the effective authorization snapshot of the request.

        The snapshot is built at most once and reused by every later
        authorization check performed during the same request.

        Returns
        -------
        IAuthorizationSnapshot
            Immutable view of the permissions, roles and abilities that
            apply to the current request.
        """
