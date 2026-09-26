import secrets
from typing import TYPE_CHECKING
from uuid import UUID
from orionis.auth.contracts.identity_provider import IIdentityProvider
from orionis.auth.contracts.session_guard import ISessionGuard
from orionis.auth.entities.guard_result import GuardResult
from orionis.auth.exceptions import AuthException
from orionis.auth.remember import RememberMe
from orionis.auth.tokens.functions import hash_token_secret
from orionis.foundation.config.auth.enums.guards import Guards
from orionis.foundation.contracts.application import IApplication

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.auth.contracts.authenticatable import IAuthenticatable
    from orionis.http.request import Request
    from orionis.session.contracts.session import ISession

# Fallback applied when the configuration section is absent.
_DEFAULT_SESSION_KEY: str = "_auth_identifier"

class SessionGuard(ISessionGuard):
    """
    Resolve the identity of web requests from the HTTP session.

    The guard never implements its own session storage: it reads and
    writes the session started by ``StartSessionMiddleware`` and reachable
    through ``request.state.session``.

    Concurrency
    -----------
    The guard is stateless and safe as a singleton. All per request state
    lives in the session object owned by the request itself.
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = (
        "__csrf_key", "__csrf_length", "__identities", "__remember", "__session_key",
    )

    def __init__(self, app: IApplication, identities: IIdentityProvider) -> None:
        """
        Initialise the guard from the authentication configuration.

        Parameters
        ----------
        app : IApplication
            Application exposing the ``auth.session`` configuration.
        identities : IIdentityProvider
            Provider turning a stored identifier into an identity.

        Returns
        -------
        None
            Only the session key and the provider are retained.
        """
        self.__session_key: str = (
            app.config("auth.session.key") or _DEFAULT_SESSION_KEY
        )
        self.__identities = identities
        self.__csrf_key: str = app.config("http.csrf.session_key") or "_csrf_token"
        self.__csrf_length: int = app.config("http.csrf.token_length") or 32
        self.__remember = RememberMe(app, identities)

    @property
    def name(self) -> str:
        """
        Return the configuration name of this guard.

        Returns
        -------
        str
            Always ``"session"``.
        """
        return Guards.SESSION.value

    async def resolve(self, request: Request) -> GuardResult | None:
        """
        Resolve the identity remembered in the session.

        A session pointing at an identity that no longer exists is
        cleaned up so the next request starts as a guest.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.

        Returns
        -------
        GuardResult | None
            Resolved identity, or ``None`` when the request is anonymous.
        """
        session = self.__session(request)
        if session is None:
            return None

        identifier = session.get(self.__session_key)
        if identifier is None:
            return await self.__restoreRemembered(request)

        identity = await self.__identities.retrieveById(identifier)
        fingerprint = session.get(self.__session_key + "_password")
        if (
            identity is None
            or not isinstance(fingerprint, str)
            or not secrets.compare_digest(
                fingerprint, hash_token_secret(identity.getAuthPassword()),
            )
        ):
            session.forget(self.__session_key)
            session.forget(self.__session_key + "_password")
            return await self.__restoreRemembered(request)

        return GuardResult(identity=identity, guard=Guards.SESSION.value)

    async def attempt(
        self,
        request: Request,
        credentials: Mapping[str, object],
        *, remember: bool = False,
    ) -> IAuthenticatable | None:
        """
        Validate credentials and start an authenticated session.

        Parameters
        ----------
        request : Request
            Incoming HTTP request owning the session.
        credentials : Mapping[str, object]
            Submitted credentials.
        remember : bool, optional
            Persist a revocable login credential after password verification.

        Returns
        -------
        IAuthenticatable | None
            Authenticated identity, or ``None`` when the credentials do
            not match. The answer never reveals whether the account
            exists or the password was wrong.
        """
        identity = await self.__identities.retrieveByCredentials(credentials)

        # The identity provider burns the hashing cost on a worker thread.
        valid = await self.__identities.validateCredentials(identity, credentials)
        if not valid or identity is None:
            return None

        # Missing, null and false status values all deny authentication.
        # Keep the status check after password verification so inactive
        # accounts follow the same hashing path as active accounts.
        if getattr(identity, "active", None) is not True:
            return None

        if remember:
            await self.__remember.issue(request, identity)
        else:
            await self.__remember.forget(request, identity)
        self.login(request, identity)
        return identity

    async def __restoreRemembered(self, request: Request) -> GuardResult | None:
        """
        Restore an identity from a persistent credential.

        Parameters
        ----------
        request : Request
            Incoming request carrying the remember-me credential.

        Returns
        -------
        GuardResult | None
            Authenticated session result, or ``None`` if restoration fails.
        """
        identity = await self.__remember.restore(request)
        if identity is None:
            return None
        self.login(request, identity)
        return GuardResult(identity=identity, guard=Guards.SESSION.value)

    def login(self, request: Request, identity: IAuthenticatable) -> None:
        """
        Persist an identity in the session of the current request.

        Parameters
        ----------
        request : Request
            Incoming HTTP request owning the session.
        identity : IAuthenticatable
            Identity to remember for subsequent requests.

        Returns
        -------
        None
            The session is mutated as a side effect.

        Raises
        ------
        AuthException
            When the request has no session, which means the route is not
            part of the web pipeline, or the identity has no persisted key.
        """
        session = self.__session(request)
        if session is None:
            error_msg = (
                "Session authentication requires a session. Make sure the "
                "route belongs to the web pipeline."
            )
            raise AuthException(error_msg)

        identifier = identity.getAuthIdentifier()
        if (
            not isinstance(identifier, (int, str, UUID))
            or isinstance(identifier, bool)
            or not str(identifier)
        ):
            error_msg = "Session login requires a persisted identity."
            raise AuthException(error_msg)
        session.regenerate()
        session.put(self.__session_key, str(identifier))
        session.put(
            self.__session_key + "_password",
            hash_token_secret(identity.getAuthPassword()),
        )
        csrf = secrets.token_urlsafe(self.__csrf_length)
        session.put(self.__csrf_key, csrf)
        request.state.csrf_token = csrf

    async def logout(self, request: Request) -> None:
        """
        Drop the authenticated state from the session.

        Parameters
        ----------
        request : Request
            Incoming HTTP request owning the session.

        Returns
        -------
        None
            The persistent credential is revoked before invalidating the
            session and clearing both cookies through the web pipeline.
        """
        session = self.__session(request)
        if session is None:
            self.__remember.clearCookie(request)
            return

        await self.__remember.revoke(request, session.get(self.__session_key))
        session.forget(self.__session_key)
        session.forget(self.__session_key + "_password")
        session.invalidate()

    @staticmethod
    def __session(request: Request) -> ISession | None:
        """
        Return the session attached to a request, when present.

        Parameters
        ----------
        request : Request
            Incoming HTTP request.

        Returns
        -------
        ISession | None
            Session started by the web pipeline, or ``None`` for routes
            that do not start one.
        """
        return getattr(request.state, "session", None)
