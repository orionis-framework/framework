from typing import TYPE_CHECKING
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import (
    authentication_lock,
    bind_auth_context,
    current_auth_context,
)
from orionis.auth.contracts.authorizable import IAuthorizable
from orionis.auth.contracts.authorizer import IAuthorizer
from orionis.auth.contracts.manager import IAuthManager
from orionis.auth.contracts.permission_repository import IPermissionRepository
from orionis.auth.contracts.session_guard import ISessionGuard
from orionis.auth.contracts.token_repository import IAccessTokenRepository
from orionis.auth.exceptions import (
    AuthException,
    AuthenticationException,
    AuthorizationException,
    GuardNotFoundException,
)
from orionis.auth.guards.token_guard import TokenGuard
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext
from orionis.foundation.contracts.application import IApplication
from orionis.http.request import Request

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import datetime
    from orionis.auth.contracts.authenticatable import IAuthenticatable
    from orionis.auth.contracts.context import IAuthenticationContext
    from orionis.auth.contracts.guard import IGuard
    from orionis.auth.contracts.policy import IPolicy
    from orionis.auth.contracts.snapshot import IAuthorizationSnapshot
    from orionis.auth.entities.new_access_token import NewAccessToken

class AuthManager(IAuthManager):
    """
    Expose authentication and authorization to application code.

    The manager owns no per request state. ``user()``, ``can()`` and
    friends read the context bound to the container scope of the running
    request, so registering the manager as a singleton is safe even
    though several requests share it concurrently.

    Concurrency
    -----------
    Guards, the authorizer and the repositories are stateless. Login and
    logout mutate the session of their own request and rebind the context
    of that scope only, so a request can never observe the identity of
    another one.
    """

    # ruff: noqa: TC001 (Dependency Injection)

    __slots__ = (
        "__authorizer",
        "__default_guard",
        "__guards",
        "__permissions",
        "__session_guard",
        "__tokens",
    )

    def __init__(  # noqa: PLR0913
        self,
        app: IApplication,
        authorizer: IAuthorizer,
        permissions: IPermissionRepository,
        session_guard: ISessionGuard,
        token_guard: TokenGuard,
        tokens: IAccessTokenRepository,
    ) -> None:
        """
        Initialise the manager with the configured collaborators.

        Parameters
        ----------
        app : IApplication
            Application exposing the ``auth`` configuration.
        authorizer : IAuthorizer
            Component answering permission, role and policy questions.
        permissions : IPermissionRepository
            Source the authorization snapshot is built from.
        session_guard : ISessionGuard
            Guard backing web authentication.
        token_guard : TokenGuard
            Guard backing personal access token authentication.
        tokens : IAccessTokenRepository
            Store used to issue and revoke personal access tokens.

        Returns
        -------
        None
            The guard registry is built once, at boot time.
        """
        self.__authorizer = authorizer
        self.__permissions = permissions
        self.__tokens = tokens
        self.__session_guard = session_guard

        # Pre-build the registry so guard resolution is a dict lookup and
        # never reflection on the hot path.
        self.__guards: dict[str, IGuard] = {
            session_guard.name: session_guard,
            token_guard.name: token_guard,
        }
        self.__default_guard: str = (
            app.config("auth.default") or session_guard.name
        )

    # ── Authentication state ──────────────────────────────────────────

    def context(self) -> IAuthenticationContext:
        """
        Return the authentication context of the current request.

        Returns
        -------
        IAuthenticationContext
            Context bound to the active scope, or the shared guest
            context outside a request.
        """
        return current_auth_context()

    def user(self) -> IAuthenticatable | None:
        """
        Return the identity authenticated for the current request.

        Returns
        -------
        IAuthenticatable | None
            Authenticated identity, or ``None`` for a guest request.
        """
        return current_auth_context().identity

    def identifier(self) -> object | None:
        """
        Return the identifier of the authenticated identity.

        Returns
        -------
        object | None
            Identifier of the identity, or ``None`` for a guest request.
        """
        return current_auth_context().identifier()

    def check(self) -> bool:
        """
        Report whether the current request is authenticated.

        Returns
        -------
        bool
            True when an identity was resolved by a guard.
        """
        return current_auth_context().isAuthenticated

    def guest(self) -> bool:
        """
        Report whether the current request is anonymous.

        Returns
        -------
        bool
            True when no identity backs the request.
        """
        return current_auth_context().isGuest

    def guard(self, name: str | None = None) -> IGuard:
        """
        Return a configured guard by name.

        Parameters
        ----------
        name : str | None, optional
            Guard name. ``None`` selects the configured default guard.

        Returns
        -------
        IGuard
            Guard registered under the requested name.

        Raises
        ------
        GuardNotFoundException
            When no guard is registered under the given name.
        """
        key = name or self.__default_guard
        guard = self.__guards.get(key)
        if guard is None:
            error_msg = (
                f"Authentication guard '{key}' is not registered. "
                f"Available guards: {sorted(self.__guards)!s}."
            )
            raise GuardNotFoundException(error_msg)
        return guard

    # ── Session lifecycle ─────────────────────────────────────────────

    async def attempt(
        self, credentials: Mapping[str, object], *, remember: bool = False,
    ) -> bool:
        """
        Authenticate the current request from submitted credentials.

        Credential based login is a session operation, so it always runs
        through the session guard regardless of the default guard.

        Parameters
        ----------
        credentials : Mapping[str, object]
            Submitted credentials, typically username and password.
        remember : bool, optional
            Persist a revocable credential for later browser sessions.

        Returns
        -------
        bool
            True when the credentials matched and the session started.
        """
        request = self.__request()
        async with authentication_lock():
            identity = await self.__session_guard.attempt(
                request, credentials, remember=remember,
            )
            if identity is None:
                return False

            self.__rebind(identity, self.__session_guard.name)
            return True

    async def login(self, identity: IAuthenticatable) -> None:
        """
        Authenticate an identity without verifying credentials.

        Parameters
        ----------
        identity : IAuthenticatable
            Identity to remember for subsequent requests.

        Returns
        -------
        None
            The session and the request context are updated.
        """
        request = self.__request()
        async with authentication_lock():
            self.__session_guard.login(request, identity)
            self.__rebind(identity, self.__session_guard.name)

    async def logout(self) -> None:
        """
        Drop the authenticated state of the current request.

        Returns
        -------
        None
            The session is invalidated and the context becomes a guest.
        """
        request = self.__request()
        async with authentication_lock():
            await self.__session_guard.logout(request)
            bind_auth_context(AuthenticationContext(guard=self.__session_guard.name))

    # ── Authorization ─────────────────────────────────────────────────

    async def authorization(self) -> IAuthorizationSnapshot:
        """
        Return the effective authorization snapshot of the request.

        Returns
        -------
        IAuthorizationSnapshot
            Immutable view of permissions, roles and token abilities.
        """
        return await current_auth_context().authorization()

    async def can(self, permission: str) -> bool:
        """
        Report whether the current request grants a permission.

        Parameters
        ----------
        permission : str
            Permission name to evaluate.

        Returns
        -------
        bool
            True when the permission is granted.
        """
        return await self.__authorizer.can(current_auth_context(), permission)

    async def cannot(self, permission: str) -> bool:
        """
        Report whether the current request lacks a permission.

        Parameters
        ----------
        permission : str
            Permission name to evaluate.

        Returns
        -------
        bool
            True when the permission is not granted.
        """
        granted = await self.can(permission)
        return not granted

    async def canAny(self, permissions: Iterable[str]) -> bool:
        """
        Report whether at least one permission is granted.

        Parameters
        ----------
        permissions : Iterable[str]
            Permission names to evaluate.

        Returns
        -------
        bool
            True when at least one permission is granted.
        """
        return await self.__authorizer.canAny(
            current_auth_context(), permissions,
        )

    async def canAll(self, permissions: Iterable[str]) -> bool:
        """
        Report whether every permission is granted.

        Parameters
        ----------
        permissions : Iterable[str]
            Permission names to evaluate.

        Returns
        -------
        bool
            True when every permission is granted.
        """
        return await self.__authorizer.canAll(
            current_auth_context(), permissions,
        )

    async def hasRole(self, role: str) -> bool:
        """
        Report whether the identity owns a role.

        Parameters
        ----------
        role : str
            Role name to evaluate.

        Returns
        -------
        bool
            True when the role is assigned to the identity.
        """
        return await self.__authorizer.hasRole(current_auth_context(), role)

    async def authorize(self, permission: str) -> None:
        """
        Require a permission or abort the current operation.

        Parameters
        ----------
        permission : str
            Permission name to require.

        Returns
        -------
        None
            Nothing is returned when the permission is granted.

        Raises
        ------
        AuthenticationException
            When the request carries no authenticated identity.
        AuthorizationException
            When the identity is authenticated but lacks the permission.
        """
        context = current_auth_context()
        if context.isGuest:
            error_msg = "Unauthenticated." # NOSONAR
            raise AuthenticationException(error_msg)

        granted = await self.__authorizer.can(context, permission)
        if not granted:
            error_msg = "This action is unauthorized."
            raise AuthorizationException(error_msg)

    async def allows(self, ability: str, resource: object) -> bool:
        """
        Evaluate a policy ability against a resource.

        Parameters
        ----------
        ability : str
            Ability declared by the policy of the resource.
        resource : object
            Resource instance, or the resource class.

        Returns
        -------
        bool
            True when the policy allows the operation.
        """
        return await self.__authorizer.allows(
            current_auth_context(), ability, resource,
        )

    async def denies(self, ability: str, resource: object) -> bool:
        """
        Report whether a policy ability is denied for a resource.

        Parameters
        ----------
        ability : str
            Ability declared by the policy of the resource.
        resource : object
            Resource instance, or the resource class.

        Returns
        -------
        bool
            True when the policy denies the operation.
        """
        allowed = await self.allows(ability, resource)
        return not allowed

    async def authorizeResource(self, ability: str, resource: object) -> None:
        """
        Require a policy ability or abort the current operation.

        Parameters
        ----------
        ability : str
            Ability declared by the policy of the resource.
        resource : object
            Resource instance, or the resource class.

        Returns
        -------
        None
            Nothing is returned when the policy allows the operation.

        Raises
        ------
        AuthenticationException
            When the request carries no authenticated identity.
        AuthorizationException
            When the policy denies the operation.
        """
        context = current_auth_context()
        if context.isGuest:
            error_msg = "Unauthenticated."
            raise AuthenticationException(error_msg)

        allowed = await self.__authorizer.allows(context, ability, resource)
        if not allowed:
            error_msg = "This action is unauthorized."
            raise AuthorizationException(error_msg)

    def registerPolicy(self, resource: type, policy: type[IPolicy]) -> None:
        """
        Bind a policy class to a resource type.

        Parameters
        ----------
        resource : type
            Resource class protected by the policy.
        policy : type[IPolicy]
            Policy class implementing the abilities.

        Returns
        -------
        None
            The policy registry is updated as a side effect.
        """
        self.__authorizer.registerPolicy(resource, policy)

    # ── Personal access tokens ────────────────────────────────────────

    async def createToken(
        self,
        name: str,
        *,
        tokenable: IAuthorizable | None = None,
        abilities: Iterable[str] | None = None,
        expires_at: datetime | None = None,
    ) -> NewAccessToken:
        """
        Issue a personal access token.

        Parameters
        ----------
        name : str
            Human readable label describing the token.
        tokenable : IAuthorizable | None, optional
            Identity owning the token. ``None`` uses the identity
            authenticated for the current request.
        abilities : Iterable[str] | None, optional
            Abilities the token may use. ``None`` keeps the full
            authorization of the identity.
        expires_at : datetime | None, optional
            Moment the token stops being accepted.

        Returns
        -------
        NewAccessToken
            Stored token metadata plus its plain text value.

        Raises
        ------
        AuthenticationException
            When no identity is available to own the token.
        AuthorizationException
            When a token-authenticated request tries to issue another token.
        AuthException
            When the identity cannot own tokens because it does not
            implement :class:`IAuthorizable`.
        """
        context = current_auth_context()
        if context.credentialId is not None:
            error_msg = "Token authentication cannot issue personal access tokens."
            raise AuthorizationException(error_msg)
        owner = tokenable if tokenable is not None else context.identity
        if owner is None:
            error_msg = "Unauthenticated."
            raise AuthenticationException(error_msg)

        if not isinstance(owner, IAuthorizable):
            error_msg = (
                "Personal access tokens require an identity implementing "
                "IAuthorizable."
            )
            raise AuthException(error_msg)

        return await self.__tokens.create(
            owner,
            name,
            abilities=abilities,
            expires_at=expires_at,
        )

    async def revokeCurrentToken(self) -> bool:
        """
        Revoke the token that authenticated the current request.

        Returns
        -------
        bool
            True when a token was revoked by this call.
        """
        context = current_auth_context()
        credential = context.credentialId
        if credential is None:
            return False
        async with authentication_lock():
            context = current_auth_context()
            credential = context.credentialId
            if credential is None:
                return False
            revoked = await self.__tokens.revoke(credential)
            bind_auth_context(AuthenticationContext(guard=context.guard))
            return revoked

    # ── Internals ─────────────────────────────────────────────────────

    def __rebind(self, identity: IAuthenticatable, guard: str) -> None:
        """
        Bind a freshly authenticated identity to the current scope.

        Parameters
        ----------
        identity : IAuthenticatable
            Identity that just authenticated.
        guard : str
            Name of the guard that authenticated it.

        Returns
        -------
        None
            The scope is updated as a side effect.
        """
        bind_auth_context(
            AuthenticationContext(
                identity=identity,
                guard=guard,
                repository=self.__permissions,
            ),
        )

    @staticmethod
    def __request() -> Request:
        """
        Return the request bound to the current container scope.

        Returns
        -------
        Request
            Request being handled right now.

        Raises
        ------
        AuthException
            When the caller is not inside an HTTP request, so no session
            is available to log in or out.
        """
        scope = ScopedContext.getCurrentScope()
        if isinstance(scope, ScopeManager) and scope.isActive:
            request = scope[Request]
            if request is not None:
                return request

        error_msg = (
            "No active HTTP request. Session authentication can only be "
            "performed while handling a request."
        )
        raise AuthException(error_msg)
