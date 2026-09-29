from typing import TYPE_CHECKING
from orionis.auth.contracts.guard import IGuard
from orionis.auth.contracts.identity_provider import IIdentityProvider
from orionis.auth.contracts.token_repository import IAccessTokenRepository
from orionis.auth.entities.guard_result import GuardResult
from orionis.foundation.config.auth.enums.guards import Guards

if TYPE_CHECKING:
    from orionis.http.request import Request

class TokenGuard(IGuard):
    """
    Resolve the identity of API requests from a personal access token.

    The token travels in the standard header::

        Authorization: Bearer <token>

    Tokens are opaque, revocable and optionally expiring. No signed
    payload such as a JWT is involved, so revocation is immediate.

    Concurrency
    -----------
    The guard is stateless and safe as a singleton. The only write it
    performs is the ``last_used_at`` update, issued as a single statement
    where the last writer legitimately wins.
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = ("__identities", "__tokens")

    def __init__(
        self,
        tokens: IAccessTokenRepository,
        identities: IIdentityProvider,
    ) -> None:
        """
        Initialise the guard with its collaborators.

        Parameters
        ----------
        tokens : IAccessTokenRepository
            Store used to look tokens up and mark them as used.
        identities : IIdentityProvider
            Provider turning a token owner into an identity.

        Returns
        -------
        None
            Only the collaborators are retained.
        """
        self.__tokens = tokens
        self.__identities = identities

    @property
    def name(self) -> str:
        """
        Return the configuration name of this guard.

        Returns
        -------
        str
            Always ``"token"``.
        """
        return Guards.TOKEN.value

    async def resolve(self, request: Request) -> GuardResult | None:
        """
        Resolve the identity owning the presented access token.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.

        Returns
        -------
        GuardResult | None
            Resolved identity together with the abilities of the token,
            or ``None`` when the request carries no usable token.
        """
        plain_text = request.bearerToken
        if not plain_text:
            return None

        # Unknown, revoked and expired tokens are indistinguishable here.
        record = await self.__tokens.findByPlainText(plain_text)
        if record is None:
            return None

        identity = await self.__identities.retrieveById(record.tokenable_id)
        if identity is None:
            return None

        # Refuse a token issued for a different kind of owner.
        describe = getattr(identity, "getAuthorizableType", None)
        identify = getattr(identity, "getAuthorizableId", None)
        if (
            not callable(describe)
            or not callable(identify)
            or describe() != record.tokenable_type
            or str(identify()) != str(record.tokenable_id)
        ):
            return None

        if not await self.__tokens.touch(record.id):
            return None

        return GuardResult(
            identity=identity,
            guard=Guards.TOKEN.value,
            abilities=record.abilities,
            credential_id=record.id,
        )
