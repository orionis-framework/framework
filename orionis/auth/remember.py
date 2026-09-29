import re
import secrets
import time
from typing import TYPE_CHECKING
from orionis.auth.contracts.identity_provider import IIdentityProvider
from orionis.auth.exceptions import AuthException
from orionis.auth.tokens.functions import hash_token_secret
from orionis.foundation.config.auth.entities.remember import RememberAuth
from orionis.foundation.contracts.application import IApplication

if TYPE_CHECKING:
    from orionis.auth.contracts.authenticatable import IAuthenticatable
    from orionis.http.request import Request
    from orionis.http.responses import Response

_MAX_COOKIE_LENGTH = 512
_COOKIE_STATE = "_auth_remember_cookie"
_COOKIE_PATTERN = re.compile(r"(.{1,255})\|(\d{1,12})\|([A-Za-z0-9_-]{43})")

class RememberMe:
    """Store expiring token digests and rotate them on persistent login."""

    # ruff: noqa: TC001, PLR0911 (Dependency injection and fail-closed validation)

    # Load remember-me settings and retain the stateless identity provider.
    def __init__(self, app: IApplication, identities: IIdentityProvider) -> None:
        """
        Initialize persistent-login settings and dependencies.

        Parameters
        ----------
        app : IApplication
            Application exposing the remember-me and session configuration.
        identities : IIdentityProvider
            Provider used to retrieve identities and update remember tokens.

        Returns
        -------
        None
            Settings and the identity provider are retained on the instance.

        Raises
        ------
        ValueError
            If the remember cookie name matches the session cookie name.
        """
        self.settings = RememberAuth(**(app.config("auth.remember") or {}))
        if self.settings.cookie == app.config("session.cookie"):
            error_msg = "The remember cookie must differ from the session cookie."
            raise ValueError(error_msg)
        self.identities = identities

    # Bind the cookie value to its identity, expiry, and password hash.
    @staticmethod
    def _stored(cookie: str, identity: IAuthenticatable, expiry: int) -> str:
        """
        Bind a credential to its identity, expiry, and password hash.

        Parameters
        ----------
        cookie : str
            Public remember-cookie value.
        identity : IAuthenticatable
            Identity that owns the credential.
        expiry : int
            Unix timestamp when the credential expires.

        Returns
        -------
        str
            Versioned digest bound to the cookie and identity password hash.
        """
        digest = hash_token_secret(cookie + "|" + identity.getAuthPassword())
        return f"v1:{expiry}:{digest}"

    # Store cookie changes until the response can emit a Set-Cookie header.
    def _queue(self, request: Request, value: str, max_age: int) -> None:
        """
        Queue a cookie change on the current request.

        Parameters
        ----------
        request : Request
            Request that owns the pending response state.
        value : str
            Cookie value to issue, or an empty string to clear it.
        max_age : int
            Cookie lifetime in seconds; zero expires the cookie immediately.

        Returns
        -------
        None
            Cookie attributes are stored on the request state.
        """
        setattr(request.state, _COOKIE_STATE, {
            "key": self.settings.cookie,
            "value": value,
            "max_age": max_age,
            "expires": 0 if max_age == 0 else None,
            "path": "/",
            "http_only": True,
            "secure": self.settings.secure,
            "same_site": "lax",
        })

    # Queue expiration of this browser's credential without changing others.
    def clearCookie(self, request: Request) -> None:
        """
        Queue expiration of the current browser's persistent credential.

        Parameters
        ----------
        request : Request
            Request that will emit the expired cookie.

        Returns
        -------
        None
            An expired cookie is queued on the request state.
        """
        self._queue(request, "", 0)

    # Replace the stored credential only after the caller verifies a password.
    async def issue(self, request: Request, identity: IAuthenticatable) -> None:
        """
        Issue a persistent credential after password verification.

        Parameters
        ----------
        request : Request
            Request that will receive the remember cookie.
        identity : IAuthenticatable
            Active identity whose prior remembered credential is replaced.

        Returns
        -------
        None
            The stored token is updated and its cookie is queued.

        Raises
        ------
        AuthException
            If HTTPS is required but unavailable, or token persistence fails.
        """
        if self.settings.secure and getattr(request, "scheme", "") != "https":
            error_msg = (
                "Remember-me requires HTTPS with auth.remember.secure=True."
            )
            raise AuthException(error_msg)
        expiry = int(time.time()) + self.settings.lifetime * 60
        cookie = self._generate(identity, expiry)
        stored = self._stored(cookie, identity, expiry)
        updated = await self.identities.updateRememberToken(
            identity, getattr(identity, "remember_token", None), stored,
        )
        if not updated:
            error_msg = (
                "The identity provider could not persist a remembered login."
            )
            raise AuthException(error_msg)
        self._queue(request, cookie, self.settings.lifetime * 60)

    # Generate a selector, expiry, and cryptographically random secret.
    @staticmethod
    def _generate(identity: IAuthenticatable, expiry: int) -> str:
        """
        Create a cookie value containing an identity, expiry, and secret.

        Parameters
        ----------
        identity : IAuthenticatable
            Identity that owns the persistent credential.
        expiry : int
            Unix timestamp when the credential expires.

        Returns
        -------
        str
            Cookie value containing the identity selector and random secret.
        """
        return f"{identity.getAuthIdentifier()}|{expiry}|{secrets.token_urlsafe(32)}"

    # Validate and rotate a presented credential without extending its deadline.
    async def restore(self, request: Request) -> IAuthenticatable | None:
        """
        Restore an identity by validating and rotating its cookie.

        Parameters
        ----------
        request : Request
            Request carrying the remember cookie.

        Returns
        -------
        IAuthenticatable | None
            Restored identity, or ``None`` when the cookie is invalid, expired,
            stale, or could not be rotated.
        """
        if self.settings.secure and getattr(request, "scheme", "") != "https":
            return None
        cookie = getattr(request, "cookies", {}).get(self.settings.cookie)
        if not isinstance(cookie, str) or not cookie:
            return None
        match = (
            _COOKIE_PATTERN.fullmatch(cookie)
            if len(cookie) <= _MAX_COOKIE_LENGTH else None
        )
        if match is None:
            self.clearCookie(request)
            return None
        identifier, expiration, _secret = match.groups()
        expiry = int(expiration)
        remaining = expiry - int(time.time())
        if remaining <= 0:
            self.clearCookie(request)
            return None
        identity = await self.identities.retrieveById(identifier)
        if identity is None or getattr(identity, "active", None) is not True:
            return None
        stored = getattr(identity, "remember_token", None)
        expected = self._stored(cookie, identity, expiry)
        if not isinstance(stored, str) or not secrets.compare_digest(
            stored.encode("utf-8"), expected.encode("ascii"),
        ):
            return None
        # Keep the original deadline. Browsing cannot extend it indefinitely.
        replacement = self._generate(identity, expiry)
        rotated = await self.identities.updateRememberToken(
            identity, stored, self._stored(replacement, identity, expiry),
        )
        if not rotated:
            # Another request may have won. Do not clear its replacement cookie.
            return None
        remaining = expiry - int(time.time())
        if remaining <= 0:
            self.clearCookie(request)
            return None
        self._queue(request, replacement, remaining)
        return identity

    # Revoke the identity's token before queuing removal of the browser cookie.
    async def revoke(self, request: Request, identifier: object) -> None:
        """
        Revoke a remembered credential and clear the browser cookie.

        Parameters
        ----------
        request : Request
            Request that will emit the cleared cookie.
        identifier : object
            Persisted identity identifier associated with the current session.

        Returns
        -------
        None
            The server-side token is revoked when its identity still exists.
        """
        if identifier is not None:
            identity = await self.identities.retrieveById(identifier)
            if identity is not None:
                await self.forget(request, identity)
        self.clearCookie(request)

    # Disable persistent login for an identity already verified by the caller.
    async def forget(self, request: Request, identity: IAuthenticatable) -> None:
        """
        Forget an identity's persistent credential.

        Parameters
        ----------
        request : Request
            Request that will emit the cleared cookie.
        identity : IAuthenticatable
            Identity whose remember token should be removed.

        Returns
        -------
        None
            The server-side token is cleared when present and the cookie expires.
        """
        stored = getattr(identity, "remember_token", None)
        if stored is not None:
            await self.identities.updateRememberToken(identity, stored, None)
        self.clearCookie(request)

# Apply pending remember-cookie changes to the outgoing web response.
def apply_remember_cookie(request: Request, response: Response) -> None:
    """
    Apply a queued remember-cookie change to the outgoing response.

    Parameters
    ----------
    request : Request
        Request containing a pending cookie change, if any.
    response : Response
        Response that will receive the cookie and cache-control headers.

    Returns
    -------
    None
        The response is updated only when a cookie change is pending.
    """
    cookie = getattr(request.state, _COOKIE_STATE, None)
    if cookie is not None:
        response.setCookie(**cookie)
        response.setHeader("Cache-Control", "no-store")
