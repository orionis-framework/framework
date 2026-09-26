from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import datetime
    from orionis.auth.contracts.authenticatable import IAuthenticatable
    from orionis.auth.contracts.authorizable import IAuthorizable
    from orionis.auth.contracts.context import IAuthenticationContext
    from orionis.auth.contracts.guard import IGuard
    from orionis.auth.contracts.policy import IPolicy
    from orionis.auth.contracts.snapshot import IAuthorizationSnapshot
    from orionis.auth.entities.new_access_token import NewAccessToken

class IAuthManager(ABC):
    """
    Define the public entry point of the authentication module.

    The manager holds no per request state. Every call reads the
    authentication context from the container scope opened for the
    request, so a singleton registration is safe under concurrency.
    """

    __slots__ = ()

    @abstractmethod
    def context(self) -> IAuthenticationContext:
        """
        Return the authentication context of the current request.

        Returns
        -------
        IAuthenticationContext
            Context bound to the active scope, or a shared guest context
            when the code runs outside an authenticated request.
        """

    @abstractmethod
    def user(self) -> IAuthenticatable | None:
        """
        Return the identity authenticated for the current request.

        Returns
        -------
        IAuthenticatable | None
            Authenticated identity, or ``None`` for a guest request.
        """

    @abstractmethod
    def identifier(self) -> object | None:
        """
        Return the identifier of the authenticated identity.

        Returns
        -------
        object | None
            Identifier of the identity, or ``None`` for a guest request.
        """

    @abstractmethod
    def check(self) -> bool:
        """
        Report whether the current request is authenticated.

        Returns
        -------
        bool
            True when an identity was resolved by a guard.
        """

    @abstractmethod
    def guest(self) -> bool:
        """
        Report whether the current request is anonymous.

        Returns
        -------
        bool
            True when no identity backs the request.
        """

    @abstractmethod
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

    @abstractmethod
    async def attempt(
        self, credentials: Mapping[str, object], *, remember: bool = False,
    ) -> bool:
        """
        Authenticate the current request from submitted credentials.

        Parameters
        ----------
        credentials : Mapping[str, object]
            Submitted credentials, typically username and password.
        remember : bool, optional
            Keep the browser signed in using a revocable persistent credential.

        Returns
        -------
        bool
            True when the credentials matched and the session was started.
        """

    @abstractmethod
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

    @abstractmethod
    async def logout(self) -> None:
        """
        Drop the authenticated state of the current request.

        Returns
        -------
        None
            The session and the request context are cleared.
        """

    @abstractmethod
    async def authorization(self) -> IAuthorizationSnapshot:
        """
        Return the effective authorization snapshot of the request.

        Returns
        -------
        IAuthorizationSnapshot
            Immutable view of permissions, roles and token abilities.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
        """

    @abstractmethod
    async def revokeCurrentToken(self) -> bool:
        """
        Revoke the presented token and clear this request's identity.

        Returns
        -------
        bool
            True when a token was revoked by this call. Requests
            authenticated through the session always answer ``False``.
        """
