from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.auth.contracts.authenticatable import IAuthenticatable

class IIdentityProvider(ABC):
    """Define how a persisted identity becomes an application object.

    Implementations decide where identities live. The rest of the module
    only knows this contract, so no component depends on a class named
    ``User``.
    """

    __slots__ = ()

    @abstractmethod
    async def retrieveById(self, identifier: object) -> IAuthenticatable | None:
        """Retrieve an identity by its unique identifier.

        Parameters
        ----------
        identifier : object
            Value previously returned by ``getAuthIdentifier()``.

        Returns
        -------
        IAuthenticatable | None
            Matching identity, or ``None`` when it no longer exists.
        """

    @abstractmethod
    async def retrieveByCredentials(
        self,
        credentials: Mapping[str, object],
    ) -> IAuthenticatable | None:
        """Retrieve an identity matching the non secret credentials.

        The password is deliberately ignored here so credential lookup and
        credential verification stay separate operations.

        Parameters
        ----------
        credentials : Mapping[str, object]
            Submitted credentials.

        Returns
        -------
        IAuthenticatable | None
            Matching identity, or ``None`` when no identity matches.
        """

    @abstractmethod
    def validateCredentials(
        self,
        identity: IAuthenticatable | None,
        credentials: Mapping[str, object],
    ) -> bool:
        """Verify the submitted secret against the stored hash.

        Implementations must spend a comparable amount of time when
        ``identity`` is ``None`` so a missing identity is not observable
        from the response time.

        Parameters
        ----------
        identity : IAuthenticatable | None
            Identity returned by ``retrieveByCredentials()``.
        credentials : Mapping[str, object]
            Submitted credentials.

        Returns
        -------
        bool
            True only when the secret matches the stored hash.
        """
