# ruff: noqa: PLR0911, TC001
# Keep runtime annotations, guarded exits, and framework integration explicit.
"""Resolve the identity of API requests from a personal access token."""

from typing import Self
from orionis.auth.contracts.guard import IGuard
from orionis.auth.concerns.functions import authorizable_key
from orionis.auth.exceptions import AuthException
from orionis.auth.contracts.identity_provider import IIdentityProvider
from orionis.auth.contracts.token_repository import IAccessTokenRepository
from orionis.auth.entities.guard_result import GuardResult
from orionis.foundation.config.auth.enums.guards import Guards

import orionis.http as _http


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

    __slots__ = ("__identities", "__tokens")
    """Declare the instance attribute slots reserved by this class."""

    def __init__(
        self: Self,
        tokens: IAccessTokenRepository,
        identities: IIdentityProvider,
    ) -> None:
        """
        Initialise the guard with its collaborators.

        Parameters
        ----------
        tokens : orionis.auth.contracts.IAccessTokenRepository
            Store used to look tokens up and mark them as used.
        identities : orionis.auth.contracts.IIdentityProvider
            Provider turning a token owner into an identity.

        Returns
        -------
        None
            No return value.
        """
        self.__tokens = tokens
        """Store used to look tokens up and mark them as used."""
        self.__identities = identities
        """Provider turning a token owner into an identity."""

    @property
    def name(self: Self) -> str:
        """
        Return the configuration name of this guard.

        Returns
        -------
        str
            Always ``"token"``.
        """
        return Guards.TOKEN.value

    async def resolve(
        self: Self,
        request: _http.Request,
    ) -> GuardResult | None:
        """
        Resolve the identity owning the presented access token.

        Parameters
        ----------
        request : orionis.http.Request
            Incoming HTTP request.

        Returns
        -------
        orionis.auth.entities.GuardResult | None
            Resolved identity together with the abilities of the token,
            or ``None`` when the request carries no usable token.
        """
        plain_text = request.bearerToken
        if not plain_text:
            return None

        # Unknown, revoked and expired tokens are indistinguishable here.
        combined = getattr(self.__tokens, "findWithIdentity", None)
        result = (
            await combined(plain_text, self.__identities)
            if combined is not None
            else NotImplemented
        )
        if result is NotImplemented:
            record = await self.__tokens.findByPlainText(plain_text)
            if record is None:
                return None
            identity = await self.__identities.retrieveById(record.tokenable_id)
        elif result is None:
            return None
        else:
            record, identity = result
        if identity is None or getattr(identity, "active", True) is not True:
            return None

        # Refuse a token issued for a different kind of owner.
        try:
            owner_key = authorizable_key(identity)
        except AuthException:
            return None
        if owner_key != (record.tokenable_type, record.tokenable_id):
            return None

        if not await self.__tokens.touch(record.id):
            return None

        return GuardResult(
            identity=identity,
            guard=Guards.TOKEN.value,
            abilities=record.abilities,
            credential_id=record.id,
        )
