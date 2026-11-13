# ruff: noqa: ARG002, PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import asyncio
from typing import TYPE_CHECKING, cast
from orionis.auth.context.context import GUEST_CONTEXT, AuthenticationContext
from orionis.auth.context.functions import bind_auth_context, current_auth_context
from orionis.auth.contracts.context import IAuthenticationContext
from orionis.auth.exceptions import AuthException
from orionis.container.context.manager import ScopeManager
from orionis.container.context.scope import ScopedContext
from orionis.session.contracts.session import ISession
from orionis.session.session import Session
from orionis.support.facades.session import Session as SessionFacade
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.auth.contracts.authenticatable import IAuthenticatable
    from orionis.auth.contracts.permission_repository import IPermissionRepository


class _ScopelessTestCase(TestCase):
    """Base case running without the ambient scope of the test runner.

    The reactor resolves its own services inside a container scope, and
    that scope object is shared by every test context. Detaching from it
    keeps each test observing a pristine, request-free environment.
    """

    def setUp(self) -> None:
        """Detach the current context from any ambient scope.

        Returns
        -------
        None
            No return value.
        """
        self._scope_token = ScopedContext.setCurrentScope(None)
        self.addCleanup(ScopedContext.reset, self._scope_token)


class _Identity:
    """Identity double exposing only what the context needs."""

    __slots__ = ("identifier",)

    def __init__(self, identifier: int) -> None:
        """Store the identifier answered by the contract method.

        Parameters
        ----------
        identifier : int
            Value supplied for ``identifier``.

        Returns
        -------
        None
            No return value.
        """
        self.identifier = identifier

    def getAuthIdentifierName(self) -> str:
        """Return the attribute holding the identifier.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return "identifier"

    def getAuthIdentifier(self) -> object:
        """Return the identifier of this identity.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self.identifier

    def getAuthPassword(self) -> str:
        """Return an empty hash; credentials are irrelevant here.

        Returns
        -------
        str
            Value produced by the helper.
        """
        return ""


class _CountingRepository:
    """Permission repository double counting how often it is queried."""

    __slots__ = ("calls", "entered", "gate", "permissions", "roles")

    def __init__(
        self,
        permissions: tuple[str, ...] = (),
        roles: tuple[str, ...] = (),
        *,
        gate: asyncio.Event | None = None,
    ) -> None:
        """Configure the answer and an optional completion gate.

        Parameters
        ----------
        permissions : tuple[str, ...]
            Value supplied for ``permissions``.
        roles : tuple[str, ...]
            Value supplied for ``roles``.
        gate : asyncio.Event | None
            Event that releases a pending lookup, or no suspension when absent.

        Returns
        -------
        None
            No return value.
        """
        self.permissions = permissions
        self.roles = roles
        self.gate = gate
        self.entered = asyncio.Event()
        self.calls = 0

    async def loadFor(
        self,
        authorizable: object,
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Return the configured authorization once the completion gate opens.

        Parameters
        ----------
        authorizable : object
            Value supplied for ``authorizable``.

        Returns
        -------
        tuple[frozenset[str], frozenset[str]]
            Value produced by the helper.
        """
        self.calls += 1
        self.entered.set()
        if self.gate is not None:
            await self.gate.wait()
        return frozenset(self.permissions), frozenset(self.roles)


class TestAuthenticationContext(_ScopelessTestCase):
    """Validate the per request authenticated state."""

    def testImplementsTheContract(self) -> None:
        """Validate the declared contract of the context.

        Consumers depend on the interface, never on the concrete class.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(AuthenticationContext(), IAuthenticationContext)

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """Validate that the context stays dictionary free.

        One context is built per request, so it must stay small.

        Returns
        -------
        None
            No return value.
        """
        self.assertFalse(hasattr(AuthenticationContext(), "__dict__"))

    def testAContextWithoutIdentityIsAGuest(self) -> None:
        """Validate the anonymous state.

        Every accessor must answer consistently for a guest.

        Returns
        -------
        None
            No return value.
        """
        context = AuthenticationContext()
        self.assertTrue(context.isGuest)
        self.assertFalse(context.isAuthenticated)
        self.assertIsNone(context.identity)
        self.assertIsNone(context.guard)
        self.assertIsNone(context.identifier())
        self.assertIsNone(context.abilities)
        self.assertIsNone(context.credentialId)

    def testAContextWithIdentityIsAuthenticated(self) -> None:
        """Validate the authenticated state.

        The guard name and the credential identifier travel with it.

        Returns
        -------
        None
            No return value.
        """
        context = AuthenticationContext(
            identity=_Identity(7),
            guard="token",
            abilities=("users.view",),
            credential_id=42,
        )
        self.assertTrue(context.isAuthenticated)
        self.assertFalse(context.isGuest)
        self.assertEqual(context.guard, "token")
        self.assertEqual(context.identifier(), 7)
        self.assertEqual(context.abilities, frozenset({"users.view"}))
        self.assertEqual(context.credentialId, 42)

    async def testAGuestResolvesToTheSharedEmptySnapshot(self) -> None:
        """Validate that guests never hit the database.

        Resolving permissions for nobody would be pure overhead.

        Returns
        -------
        None
            No return value.
        """
        repository = _CountingRepository(permissions=("users.view",))
        context = AuthenticationContext(repository=repository)

        snapshot = await context.authorization()

        self.assertEqual(snapshot.permissions, frozenset())
        self.assertEqual(repository.calls, 0)

    async def testAnAuthenticatedContextResolvesItsSnapshotOnce(self) -> None:
        """Cache the authorization snapshot after its first resolution.

        Repeated ``can()`` calls must not repeat the queries.

        Returns
        -------
        None
            No return value.
        """
        repository = _CountingRepository(
            permissions=("users.view",),
            roles=("admin",),
        )
        context = AuthenticationContext(
            identity=_Identity(1),
            guard="session",
            repository=repository,
        )

        self.assertIsNone(context._AuthenticationContext__lock)
        first = await context.authorization()
        second = await context.authorization()

        self.assertIsNotNone(context._AuthenticationContext__lock)
        self.assertIs(first, second)
        self.assertEqual(repository.calls, 1)
        self.assertTrue(first.can("users.view"))
        self.assertTrue(first.hasRole("admin"))

    async def testTheSnapshotCarriesTheCredentialAbilities(self) -> None:
        """Validate that the token restriction reaches the snapshot.

        Otherwise abilities would silently be ignored.

        Returns
        -------
        None
            No return value.
        """
        repository = _CountingRepository(
            permissions=("users.view", "users.delete"),
        )
        context = AuthenticationContext(
            identity=_Identity(1),
            guard="token",
            abilities=("users.view",),
            repository=repository,
        )

        snapshot = await context.authorization()

        self.assertTrue(snapshot.can("users.view"))
        self.assertFalse(snapshot.can("users.delete"))

    async def testConcurrentResolutionsShareASingleQuery(self) -> None:
        """Validate that the lazy snapshot is race free.

        Several coroutines of the same request may ask at once; only one
        of them may reach the database.

        Returns
        -------
        None
            No return value.
        """
        gate = asyncio.Event()
        repository = _CountingRepository(permissions=("users.view",), gate=gate)
        context = AuthenticationContext(
            identity=_Identity(1),
            guard="session",
            repository=repository,
        )

        tasks = [asyncio.create_task(context.authorization()) for _ in range(8)]
        try:
            await repository.entered.wait()
            self.assertEqual(repository.calls, 1)
            self.assertTrue(all(not task.done() for task in tasks))
            gate.set()
            snapshots = await asyncio.gather(*tasks)
            self.assertEqual(repository.calls, 1)
            self.assertEqual(len({id(item) for item in snapshots}), 1)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def testAnAuthenticatedContextWithoutRepositoryStaysEmpty(
        self,
    ) -> None:
        """Validate the defensive path when no source is wired.

        The context must degrade to "no permissions" instead of failing.

        Returns
        -------
        None
            No return value.
        """
        context = AuthenticationContext(identity=_Identity(1), guard="session")

        snapshot = await context.authorization()

        self.assertEqual(snapshot.permissions, frozenset())

    def testRepresentationNeverLeaksCredentials(self) -> None:
        """Validate that debugging output is safe to log.

        Only the guard and the identifier are exposed.

        Returns
        -------
        None
            No return value.
        """
        guest = AuthenticationContext()
        self.assertEqual(repr(guest), "AuthenticationContext(guest)")

        context = AuthenticationContext(
            identity=_Identity(7),
            guard="session",
            abilities=("secret.thing",),
        )
        text = repr(context)
        self.assertIn("session", text)
        self.assertIn("7", text)
        self.assertNotIn("secret.thing", text)


class TestAuthenticationContextBinding(_ScopelessTestCase):
    """Validate how the context is stored in the container scope."""

    async def testForkUsesIndependentScopesAndAuthorizationSnapshots(self) -> None:
        """Preserve credential limits while resolving authorization per scope.

        Returns
        -------
        None
            No return value.
        """
        identity = _Identity(7)
        repository = _CountingRepository(permissions=("users.view", "users.edit"))
        context = AuthenticationContext(
            identity=cast("IAuthenticatable", identity),
            guard="token",
            abilities=("users.view",),
            repository=cast("IPermissionRepository", repository),
            credential_id=9,
        )

        async def resolve(context: AuthenticationContext) -> object:
            """Bind one fork and retain its resolved snapshot for comparison.

            Parameters
            ----------
            context : AuthenticationContext
                Fresh context created in the parent scope.

            Returns
            -------
            object
                Independent immutable authorization snapshot.
            """
            async with ScopeManager():
                bind_auth_context(context)
                await asyncio.sleep(0)
                self.assertIs(current_auth_context().identity, identity)
                self.assertEqual(context.guard, "token")
                self.assertEqual(context.credentialId, 9)
                snapshot = await context.authorization()
                self.assertTrue(snapshot.can("users.view"))
                self.assertFalse(snapshot.can("users.edit"))
                return snapshot

        async with ScopeManager():
            bind_auth_context(context)
            original_snapshot = await context.authorization()
            first, second = context._fork(), context._fork()
            snapshots = await asyncio.gather(resolve(first), resolve(second))
            self.assertIs(current_auth_context(), context)
            self.assertIs(context.identity, identity)
            self.assertIsNot(snapshots[0], snapshots[1])
            self.assertTrue(all(item is not original_snapshot for item in snapshots))
            self.assertEqual(repository.calls, 3)
            self.assertIsNone(first.identity)
            self.assertIsNone(second.identity)

    async def testForkCannotReviveAStaleIdentity(self) -> None:
        """Ensure a closed or foreign context can only produce a guest fork.

        Returns
        -------
        None
            No return value.
        """
        context = AuthenticationContext(
            identity=cast("IAuthenticatable", _Identity(7)),
            guard="session",
        )
        async with ScopeManager():
            bind_auth_context(context)
            async with ScopeManager():
                self.assertIsNone(context._fork().identity)
        self.assertIsNone(context._fork().identity)

    async def testForkSurvivesCancellationOnlyUntilItsScopeCloses(self) -> None:
        """Restore the connection context when an invocation is cancelled.

        Returns
        -------
        None
            No return value.
        """
        context = AuthenticationContext(
            identity=cast("IAuthenticatable", _Identity(7)),
            guard="session",
        )
        entered = asyncio.Event()

        async def invocation(fork: AuthenticationContext) -> None:
            """Hold an invocation scope until cancellation.

            Parameters
            ----------
            fork : AuthenticationContext
                Invocation context copied from the parent.

            Returns
            -------
            None
                No return value.
            """
            async with ScopeManager():
                bind_auth_context(fork)
                entered.set()
                await asyncio.Event().wait()

        async with ScopeManager():
            bind_auth_context(context)
            fork = context._fork()
            task = asyncio.create_task(invocation(fork))
            await entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertIsNone(fork.identity)
            self.assertIs(current_auth_context(), context)
            self.assertEqual(context.identifier(), 7)

    def testWithoutAScopeTheGuestContextIsReturned(self) -> None:
        """Validate the answer outside an HTTP request.

        Console commands and background tasks are anonymous by default.

        Returns
        -------
        None
            No return value.
        """
        self.assertIs(current_auth_context(), GUEST_CONTEXT)

    def testBindingRequiresAnActiveScope(self) -> None:
        """Validate that a context cannot be bound out of a request.

        Storing it globally would leak between concurrent requests.

        Returns
        -------
        None
            No return value.
        """
        context = AuthenticationContext(identity=_Identity(1), guard="session")
        with self.assertRaises(AuthException):
            bind_auth_context(context)

    async def testBindingInsideAScopeIsVisibleToTheWholeRequest(self) -> None:
        """Validate the normal binding path.

        Everything running inside the scope must observe the identity.

        Returns
        -------
        None
            No return value.
        """
        context = AuthenticationContext(identity=_Identity(1), guard="session")

        async with ScopeManager():
            bind_auth_context(context)
            self.assertIs(current_auth_context(), context)

        self.assertIs(current_auth_context(), GUEST_CONTEXT)

    async def testAnEmptyScopeStillReportsAGuest(self) -> None:
        """Validate the state before the middleware runs.

        A scope without a bound context is not authenticated.

        Returns
        -------
        None
            No return value.
        """
        async with ScopeManager():
            self.assertIs(current_auth_context(), GUEST_CONTEXT)

    async def testConcurrentScopesNeverObserveEachOther(self) -> None:
        """Validate the isolation guarantee between concurrent requests.

        Two tasks binding different identities must keep seeing their
        own one across every suspension point.

        Returns
        -------
        None
            No return value.
        """
        observed: dict[str, list[object]] = {}

        async def handle(name: str, identifier: int) -> None:
            """Handle a request in the isolated test scope.

            Parameters
            ----------
            name : str
                Value supplied for ``name``.
            identifier : int
                Value supplied for ``identifier``.

            Returns
            -------
            None
                No return value.
            """
            async with ScopeManager():
                bind_auth_context(
                    AuthenticationContext(
                        identity=_Identity(identifier),
                        guard="session",
                    ),
                )
                seen = []
                for _ in range(5):
                    await asyncio.sleep(0)
                    seen.append(current_auth_context().identifier())
                observed[name] = seen

        await asyncio.gather(handle("a", 1), handle("b", 2))

        self.assertEqual(observed["a"], [1, 1, 1, 1, 1])
        self.assertEqual(observed["b"], [2, 2, 2, 2, 2])

    async def testAnInheritedClosedScopeCannotAuthenticateAgain(self) -> None:
        """Reject identity publication after the owning request has ended.

        Returns
        -------
        None
            No return value.
        """
        finished = asyncio.Event()

        async def authenticate_late() -> None:
            """Attempt authentication after the scope closes.

            Returns
            -------
            None
                No return value.
            """
            await finished.wait()
            self.assertIs(current_auth_context(), GUEST_CONTEXT)
            with self.assertRaises(AuthException):
                bind_auth_context(
                    AuthenticationContext(identity=_Identity(9), guard="session"),
                )

        async with ScopeManager():
            pending = asyncio.create_task(authenticate_late())

        finished.set()
        await pending

    async def testSessionFacadeIsIsolatedAcrossConcurrentRequests(self) -> None:
        """Read and mutate only the session of the active request.

        Returns
        -------
        None
            No return value.
        """
        barrier = asyncio.Barrier(2)

        async def handle(identifier: int) -> None:
            """Handle a request in the isolated test scope.

            Parameters
            ----------
            identifier : int
                Value supplied for ``identifier``.

            Returns
            -------
            None
                No return value.
            """
            async with ScopeManager() as scope:
                session = Session()
                session.put("owner", identifier)
                scope[ISession] = session
                await SessionFacade.pin()
                await barrier.wait()
                self.assertEqual(SessionFacade.get("owner"), identifier)
                self.assertIs(await SessionFacade.resolve(), session)
                SessionFacade.put("visited", identifier)
                await barrier.wait()
                self.assertEqual(session.get("visited"), identifier)
                SessionFacade.unpin()

        await asyncio.gather(handle(1), handle(2))
        self.assertIsNone(SessionFacade._pinned_instance)
        with self.assertRaises(RuntimeError):
            SessionFacade.get("owner")

    async def testSessionFacadeCannotEscapeAnExceptionalRequest(self) -> None:
        """Deny inherited session access once an exceptional scope has exited.

        Returns
        -------
        None
            No return value.

        """
        finished = asyncio.Event()

        async def read_late() -> None:
            """Read the session facade after the scope closes.

            Returns
            -------
            None
                No return value.
            """
            await finished.wait()
            with self.assertRaises(RuntimeError):
                await SessionFacade.resolve()

        with self.assertRaises(ValueError):
            async with ScopeManager() as scope:
                scope[ISession] = Session()
                pending = asyncio.create_task(read_late())
                error_msg = "request failed"
                raise ValueError(error_msg)

        finished.set()
        await pending

    async def testRetainedContextStopsAuthorizingAfterReplacementAndExit(self) -> None:
        """Invalidate retained context references when the owner changes or exits.

        Returns
        -------
        None
            No return value.
        """
        context = AuthenticationContext(
            identity=_Identity(1),
            guard="session",
            repository=_CountingRepository(permissions=("users.view",)),
        )
        async with ScopeManager():
            bind_auth_context(context)
            self.assertTrue((await context.authorization()).can("users.view"))
            bind_auth_context(AuthenticationContext(guard="session"))
            self.assertTrue(context.isGuest)
            self.assertFalse((await context.authorization()).can("users.view"))
        self.assertIsNone(context.identity)

    async def testContextCannotBeReusedAcrossRequests(self) -> None:
        """Reject binding the same identity context to a different scope.

        Returns
        -------
        None
            No return value.
        """
        context = AuthenticationContext(identity=_Identity(1), guard="session")
        async with ScopeManager():
            bind_auth_context(context)
        async with ScopeManager():
            with self.assertRaises(AuthException):
                bind_auth_context(context)

    async def testContextReferenceDoesNotAuthorizeAnotherActiveScope(self) -> None:
        """Deny a reference used from a different request even while its owner lives.

        Returns
        -------
        None
            No return value.
        """
        context = AuthenticationContext(identity=_Identity(1), guard="session")
        async with ScopeManager():
            bind_auth_context(context)
            self.assertTrue(context.isAuthenticated)
            async with ScopeManager():
                self.assertTrue(context.isGuest)
                self.assertIsNone(context.identifier())
            self.assertTrue(context.isAuthenticated)
