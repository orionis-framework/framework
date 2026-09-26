from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.auth.contracts.authenticatable import IAuthenticatable

class IIdentityProvider(ABC):
    """
    Define how a persisted identity becomes an application object.

    Implementations decide where identities live. The rest of the module
    only knows this contract, so no component depends on a class named
    ``User``.
    """

    __slots__ = ()

    async def updateRememberToken( # NOSONAR
        self,
        identity: IAuthenticatable,  # noqa: ARG002
        expected: str | None,  # noqa: ARG002
        token: str | None,  # noqa: ARG002
    ) -> bool:
        """
        Optionally compare and replace a persistent credential atomically.

        Providers supporting remember-me must also compare the current password
        and require an active identity when issuing a non-null token. Providers
        without persistent login support return False and issue no cookie.
        """
        return False

    @abstractmethod
    async def retrieveById(self, identifier: object) -> IAuthenticatable | None:
        """
        Retrieve an identity by its unique identifier.

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
        """
        Retrieve an identity matching the non secret credentials.

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
    async def validateCredentials(
        self,
        identity: IAuthenticatable | None,
        credentials: Mapping[str, object],
    ) -> bool:
        """
        Verify credentials without blocking the event loop.

        Parameters
        ----------
        identity : IAuthenticatable | None
            Identity whose stored password should be checked.
        credentials : Mapping[str, object]
            Submitted credentials.

        Returns
        -------
        bool
            True only when the credentials match the stored password.
        """
