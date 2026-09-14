import asyncio
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

class _ScopelessTestCase(TestCase):
    """Base case running without the ambient scope of the test runner.

    The reactor resolves its own services inside a container scope, and
    that scope object is shared by every test context. Detaching from it
    keeps each test observing a pristine, request-free environment.
    """

    def setUp(self) -> None:
        """Detach the current context from any ambient scope."""
        self._scope_token = ScopedContext.setCurrentScope(None)

    def tearDown(self) -> None:
        """Restore the ambient scope of the runner."""
        ScopedContext.reset(self._scope_token)

class _Identity:
    """Identity double exposing only what the context needs."""

    __slots__ = ("identifier",)

    def __init__(self, identifier: int) -> None:
        """Store the identifier answered by the contract method."""
        self.identifier = identifier

    def getAuthIdentifierName(self) -> str:
        """Return the attribute holding the identifier."""
        return "identifier"

    def getAuthIdentifier(self) -> object:
        """Return the identifier of this identity."""
        return self.identifier

    def getAuthPassword(self) -> str:
        """Return an empty hash; credentials are irrelevant here."""
        return ""

class _CountingRepository:
    """Permission repository double counting how often it is queried."""

    __slots__ = ("calls", "delay", "permissions", "roles")

    def __init__(
        self,
        permissions: tuple[str, ...] = (),
        roles: tuple[str, ...] = (),
        delay: float = 0.0,
    ) -> None:
        """Configure the answer and the number of suspension points."""
        self.permissions = permissions
        self.roles = roles
        self.delay = delay
        self.calls = 0

    async def loadFor(
        self,
        authorizable: object,  # noqa: ARG002
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Return the configured authorization after an optional delay."""
        self.calls += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        return frozenset(self.permissions), frozenset(self.roles)

class TestAuthenticationContext(_ScopelessTestCase):
    """Validate the per request authenticated state."""

    def testImplementsTheContract(self) -> None:
        """Validates the declared contract of the context.

        Consumers depend on the interface, never on the concrete class.
        """
        self.assertIsInstance(AuthenticationContext(), IAuthenticationContext)

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """Validates that the context stays dictionary free.

        One context is built per request, so it must stay small.
        """
        self.assertFalse(hasattr(AuthenticationContext(), "__dict__"))

    def testAContextWithoutIdentityIsAGuest(self) -> None:
        """Validates the anonymous state.

        Every accessor must answer consistently for a guest.
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
        """Validates the authenticated state.

        The guard name and the credential identifier travel with it.
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
        """Validates that guests never hit the database.

        Resolving permissions for nobody would be pure overhead.
        """
        repository = _CountingRepository(permissions=("users.view",))
        context = AuthenticationContext(repository=repository)

        snapshot = await context.authorization()

        self.assertEqual(snapshot.permissions, frozenset())
        self.assertEqual(repository.calls, 0)

    async def testAnAuthenticatedContextResolvesItsSnapshotOnce(self) -> None:
        """Validates the per request caching of the authorization.

        Repeated ``can()`` calls must not repeat the queries.
        """
        repository = _CountingRepository(
            permissions=("users.view",), roles=("admin",),
        )
        context = AuthenticationContext(
            identity=_Identity(1), guard="session", repository=repository,
        )

        first = await context.authorization()
        second = await context.authorization()

        self.assertIs(first, second)
        self.assertEqual(repository.calls, 1)
        self.assertTrue(first.can("users.view"))
        self.assertTrue(first.hasRole("admin"))

    async def testTheSnapshotCarriesTheCredentialAbilities(self) -> None:
        """Validates that the token restriction reaches the snapshot.

        Otherwise abilities would silently be ignored.
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
        """Validates that the lazy snapshot is race free.

        Several coroutines of the same request may ask at once; only one
        of them may reach the database.
        """
        repository = _CountingRepository(
            permissions=("users.view",), delay=0.01,
        )
        context = AuthenticationContext(
            identity=_Identity(1), guard="session", repository=repository,
        )

        snapshots = await asyncio.gather(
            *(context.authorization() for _ in range(8)),
        )

        self.assertEqual(repository.calls, 1)
        self.assertEqual(len({id(item) for item in snapshots}), 1)

    async def testAnAuthenticatedContextWithoutRepositoryStaysEmpty(
        self,
    ) -> None:
        """Validates the defensive path when no source is wired.

        The context must degrade to "no permissions" instead of failing.
        """
        context = AuthenticationContext(identity=_Identity(1), guard="session")

        snapshot = await context.authorization()

        self.assertEqual(snapshot.permissions, frozenset())

    def testRepresentationNeverLeaksCredentials(self) -> None:
        """Validates that debugging output is safe to log.

        Only the guard and the identifier are exposed.
        """
        guest = AuthenticationContext()
        self.assertEqual(repr(guest), "AuthenticationContext(guest)")

        context = AuthenticationContext(
            identity=_Identity(7), guard="session", abilities=("secret.thing",),
        )
        text = repr(context)
        self.assertIn("session", text)
        self.assertIn("7", text)
        self.assertNotIn("secret.thing", text)

class TestAuthenticationContextBinding(_ScopelessTestCase):
    """Validate how the context is stored in the container scope."""

    async def testWithoutAScopeTheGuestContextIsReturned(self) -> None:
        """Validates the answer outside an HTTP request.

        Console commands and background tasks are anonymous by default.
        """
        self.assertIs(current_auth_context(), GUEST_CONTEXT)

    async def testBindingRequiresAnActiveScope(self) -> None:
        """Validates that a context cannot be bound out of a request.

        Storing it globally would leak between concurrent requests.
        """
        context = AuthenticationContext(identity=_Identity(1), guard="session")
        with self.assertRaises(AuthException):
            bind_auth_context(context)

    async def testBindingInsideAScopeIsVisibleToTheWholeRequest(self) -> None:
        """Validates the normal binding path.

        Everything running inside the scope must observe the identity.
        """
        context = AuthenticationContext(identity=_Identity(1), guard="session")

        async with ScopeManager():
            bind_auth_context(context)
            self.assertIs(current_auth_context(), context)

        self.assertIs(current_auth_context(), GUEST_CONTEXT)

    async def testAnEmptyScopeStillReportsAGuest(self) -> None:
        """Validates the state before the middleware runs.

        A scope without a bound context is not authenticated.
        """
        async with ScopeManager():
            self.assertIs(current_auth_context(), GUEST_CONTEXT)

    async def testConcurrentScopesNeverObserveEachOther(self) -> None:
        """Validates the isolation guarantee between concurrent requests.

        Two tasks binding different identities must keep seeing their
        own one across every suspension point.
        """
        observed: dict[str, list[object]] = {}

        async def handle(name: str, identifier: int) -> None:
            async with ScopeManager():
                bind_auth_context(
                    AuthenticationContext(
                        identity=_Identity(identifier), guard="session",
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
        """Reject identity publication after the owning request has ended."""
        finished = asyncio.Event()

        async def authenticate_late() -> None:
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
        """Read and mutate only the session of the active request."""
        barrier = asyncio.Barrier(2)

        async def handle(identifier: int) -> None:
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
        """Deny inherited session access once an exceptional scope has exited."""
        finished = asyncio.Event()

        async def read_late() -> None:
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
        """Invalidate retained context references when the owner changes or exits."""
        context = AuthenticationContext(
            identity=_Identity(1), guard="session",
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
        """Reject binding the same identity context to a different scope."""
        context = AuthenticationContext(identity=_Identity(1), guard="session")
        async with ScopeManager():
            bind_auth_context(context)
        async with ScopeManager():
            with self.assertRaises(AuthException):
                bind_auth_context(context)

    async def testContextReferenceDoesNotAuthorizeAnotherActiveScope(self) -> None:
        """Deny a reference used from a different request even while its owner lives."""
        context = AuthenticationContext(identity=_Identity(1), guard="session")
        async with ScopeManager():
            bind_auth_context(context)
            self.assertTrue(context.isAuthenticated)
            async with ScopeManager():
                self.assertTrue(context.isGuest)
                self.assertIsNone(context.identifier())
            self.assertTrue(context.isAuthenticated)
