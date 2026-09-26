import asyncio
from collections.abc import Iterable
from typing import TYPE_CHECKING
from orionis.auth.authorization.snapshot import EMPTY_SNAPSHOT, AuthorizationSnapshot
from orionis.auth.contracts.authenticatable import IAuthenticatable
from orionis.auth.contracts.context import IAuthenticationContext
from orionis.auth.contracts.permission_repository import IPermissionRepository
from orionis.auth.exceptions import AuthException
from orionis.container.context.scope import ScopedContext

if TYPE_CHECKING:
    from orionis.auth.contracts.snapshot import IAuthorizationSnapshot
    from orionis.container.context.manager import ScopeManager

class AuthenticationContext(IAuthenticationContext):
    """
    Hold the authenticated state of one request.

    A context is created by the authentication middleware and stored in
    the container scope opened by the HTTP kernel. It is never attached
    to a singleton, so two requests running concurrently on the same
    event loop can never observe each other's identity.

    Concurrency
    -----------
    The identity, the guard name and the abilities are fixed at
    construction time. The authorization snapshot is resolved lazily
    under an ``asyncio.Lock`` owned by this context, so several
    coroutines of the same request share a single database round trip.
    """

    # ruff: noqa: TC001, TC003

    __slots__ = (
        "__abilities",
        "__credential_id",
        "__guard",
        "__identity",
        "__lock",
        "__repository",
        "__scope",
        "__snapshot",
    )

    def __init__(
        self,
        identity: IAuthenticatable | None = None,
        guard: str | None = None,
        abilities: Iterable[str] | None = None,
        repository: IPermissionRepository | None = None,
        credential_id: object | None = None,
    ) -> None:
        """
        Build the authentication context of a request.

        Parameters
        ----------
        identity : IAuthenticatable | None, optional
            Identity resolved by a guard, or ``None`` for a guest.
        guard : str | None, optional
            Name of the guard that resolved the identity.
        abilities : Iterable[str] | None, optional
            Abilities restricting the presented credential.
        repository : IPermissionRepository | None, optional
            Source used to resolve the authorization snapshot. It is only
            required for authenticated contexts.
        credential_id : object | None, optional
            Identifier of the revocable credential that authenticated the
            request, such as a personal access token.

        Returns
        -------
        None
            The context starts without a resolved snapshot.
        """
        self.__identity = identity
        self.__guard = guard
        self.__abilities: frozenset[str] | None = (
            None if abilities is None else frozenset(abilities)
        )
        self.__repository = repository
        self.__credential_id = credential_id
        self.__snapshot: IAuthorizationSnapshot | None = None
        self.__scope: ScopeManager | None = None

        # Guests resolve to the shared empty snapshot, so they never need
        # a lock nor a database round trip.
        self.__lock = asyncio.Lock() if identity is not None else None

    def _bindToScope(self, scope: ScopeManager) -> None:
        """
        Associate this context with one scope for its remaining lifetime.

        Parameters
        ----------
        scope : ScopeManager
            Active request scope publishing this context.

        Returns
        -------
        None
            Later reads verify that the context is still current in this scope.

        Raises
        ------
        AuthException
            If a context is shared between different request scopes.
        """
        if self.__scope is not None and self.__scope is not scope:
            error_msg = "An authentication context cannot be shared between scopes."
            raise AuthException(error_msg)
        self.__scope = scope

    def __isCurrent(self) -> bool:
        """
        Report whether this context still belongs to a live request.

        Returns
        -------
        bool
            False once replaced or once its owning scope has closed.
        """
        scope = self.__scope
        return scope is None or (
            scope.isActive
            and ScopedContext.getCurrentScope() is scope
            and scope[IAuthenticationContext] is self
        )

    @property
    def identity(self) -> IAuthenticatable | None:
        """
        Return the authenticated identity of the request.

        Returns
        -------
        IAuthenticatable | None
            Resolved identity, or ``None`` for a guest request.
        """
        return self.__identity if self.__isCurrent() else None

    @property
    def guard(self) -> str | None:
        """
        Return the name of the guard that resolved the identity.

        Returns
        -------
        str | None
            Guard name, or ``None`` when the request is anonymous.
        """
        return self.__guard

    @property
    def abilities(self) -> frozenset[str] | None:
        """
        Return the abilities carried by the presented credential.

        Returns
        -------
        frozenset[str] | None
            Abilities of the credential, or ``None`` when unrestricted.
        """
        return self.__abilities

    @property
    def credentialId(self) -> object | None:
        """
        Return the identifier of the credential that authenticated.

        Returns
        -------
        object | None
            Identifier of the revocable credential, or ``None`` when the
            guard uses none.
        """
        return self.__credential_id if self.__isCurrent() else None

    @property
    def isAuthenticated(self) -> bool:
        """
        Report whether the request carries an authenticated identity.

        Returns
        -------
        bool
            True when an identity was resolved by a guard.
        """
        return self.identity is not None

    @property
    def isGuest(self) -> bool:
        """
        Report whether the request is anonymous.

        Returns
        -------
        bool
            True when no identity was resolved by any guard.
        """
        return self.identity is None

    def identifier(self) -> object | None:
        """
        Return the unique identifier of the authenticated identity.

        Returns
        -------
        object | None
            Identifier of the identity, or ``None`` for a guest request.
        """
        identity = self.identity
        if identity is None:
            return None
        return identity.getAuthIdentifier()

    async def authorization(self) -> IAuthorizationSnapshot:
        """
        Return the effective authorization snapshot of the request.

        Returns
        -------
        IAuthorizationSnapshot
            Snapshot resolved at most once per request. Guests and
            contexts without a permission repository resolve to the
            shared empty snapshot.
        """
        if not self.__isCurrent():
            return EMPTY_SNAPSHOT
        snapshot = self.__snapshot
        if snapshot is not None:
            return snapshot

        identity = self.__identity
        repository = self.__repository
        lock = self.__lock
        if identity is None or repository is None or lock is None:
            self.__snapshot = EMPTY_SNAPSHOT
            return EMPTY_SNAPSHOT

        async with lock:
            # Re-check inside the lock: another coroutine of this request
            # may have resolved the snapshot while we were waiting.
            snapshot = self.__snapshot
            if snapshot is not None:
                return snapshot

            permissions, roles = await repository.loadFor(identity)
            if not self.__isCurrent():
                return EMPTY_SNAPSHOT
            snapshot = AuthorizationSnapshot(
                permissions=permissions,
                roles=roles,
                abilities=self.__abilities,
            )
            self.__snapshot = snapshot
            return snapshot

    def __repr__(self) -> str:
        """
        Return a debugging representation of the context.

        Returns
        -------
        str
            Description exposing the guard and the identifier only, never
            any credential material.
        """
        if self.identity is None:
            return "AuthenticationContext(guest)"
        return (
            f"AuthenticationContext(guard={self.__guard!r}, "
            f"identifier={self.identifier()!r})"
        )

# Shared context handed to every request nobody authenticated. It carries
# no identity and resolves to the empty snapshot, so sharing is safe.
GUEST_CONTEXT: AuthenticationContext = AuthenticationContext()
