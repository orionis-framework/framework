from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime
    from orionis.auth.contracts.authorizable import IAuthorizable
    from orionis.auth.entities.access_token import AccessToken
    from orionis.auth.entities.new_access_token import NewAccessToken

class IAccessTokenRepository(ABC):
    """Define the persistence operations of personal access tokens.

    Only a hash of the secret is stored, so a leaked database row never
    reveals a usable credential.
    """

    __slots__ = ()

    @abstractmethod
    async def create(
        self,
        tokenable: IAuthorizable,
        name: str,
        *,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken:
        """Issue a new personal access token for an identity.

        Parameters
        ----------
        tokenable : IAuthorizable
            Identity the token belongs to.
        name : str
            Human readable label describing the token.
        abilities : Iterable[str] | None, optional
            Abilities the token may use. ``None`` keeps the full
            authorization of the identity.
        expires_at : datetime | None, optional
            Moment the token stops being accepted. ``None`` falls back to
            the configured default expiration.

        Returns
        -------
        NewAccessToken
            Stored token metadata plus the plain text value, which is the
            only moment the secret is available.
        """

    @abstractmethod
    async def findByPlainText(self, plain_text: str) -> AccessToken | None:
        """Resolve a token from the value presented by the client.

        Expired and revoked tokens are treated as absent.

        Parameters
        ----------
        plain_text : str
            Value received in the ``Authorization`` header.

        Returns
        -------
        AccessToken | None
            Matching token, or ``None`` when the value is unusable.
        """

    @abstractmethod
    async def touch(self, token_id: object) -> bool:
        """Confirm token validity and record its use atomically.

        Parameters
        ----------
        token_id : object
            Identifier of the token to update.

        Returns
        -------
        bool
            True only when a non-revoked, unexpired token was updated.
        """

    @abstractmethod
    async def revoke(self, token_id: object) -> bool:
        """Revoke a single token.

        Parameters
        ----------
        token_id : object
            Identifier of the token to revoke.

        Returns
        -------
        bool
            True when a token was revoked by this call.
        """

    @abstractmethod
    async def revokeAll(self, tokenable: IAuthorizable) -> int:
        """Revoke every active token of an identity.

        Parameters
        ----------
        tokenable : IAuthorizable
            Identity whose tokens must be revoked.

        Returns
        -------
        int
            Number of tokens revoked by this call.
        """

    @abstractmethod
    async def purgeExpired(self) -> int:
        """Delete tokens that expired or were revoked.

        Returns
        -------
        int
            Number of rows removed from the store.
        """
