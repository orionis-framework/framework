import threading
from types import SimpleNamespace
from typing import Any
from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.exceptions import AuthException, IdentityProviderException
from orionis.auth.guards.session_guard import SessionGuard
from orionis.auth.identity.provider import ModelIdentityProvider
from orionis.database.connection_manager import ConnectionManager
from orionis.hashing.hash_manager import HashManager
from orionis.orm import BigInteger, Boolean, Model, String
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.table import TableDefinition
from orionis.session.session import Session
from orionis.test import TestCase

# Cheap Argon2 parameters: these tests verify behaviour, not cost.
_HASH_OPTIONS: dict[str, int] = {"memory": 32, "threads": 1, "time": 1}

class Account(Model, Authenticatable, Authorizable):
    """Identity model used by the tests in this module."""

    table = "accounts"
    timestamps = False

    id = BigInteger().primary().autoIncrement()
    email = String(255)
    password = String(255)
    active = Boolean().nullable()

class _StubApp:
    """Application stub exposing the database and auth configuration."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Store the configuration tree the stub answers from."""
        self._config = config

    def config(self, key: str | None = None) -> Any:  # noqa: ANN401
        """Resolve a dot-notated configuration key."""
        if key is None:
            return self._config
        node: Any = self._config
        for part in key.split("."):
            if not isinstance(node, dict):
                return None
            node = node.get(part)
            if node is None:
                return None
        return node

def build_app(**auth: object) -> _StubApp:
    """Build an application stub wired to an in-memory SQLite database."""
    identity = {
        "model": f"{__name__}.Account",
        "username": "email",
        "password": "password",
    }
    identity.update(auth.pop("identity", {}))
    return _StubApp({
        "database": {
            "default": "sqlite",
            "connections": {
                "sqlite": {
                    "driver": "sqlite",
                    "database": ":memory:",
                    "prefix": "",
                },
            },
        },
        "hashing": {"driver": "argon2", "argon2": _HASH_OPTIONS},
        "auth": {
            "default": "session",
            "identity": identity,
            "session": {"key": "_auth_identifier", "redirect_to": None},
            "tokens": {},
            **auth,
        },
    })

def accounts_table() -> TableDefinition:
    """Build the physical ``accounts`` table."""
    columns = {
        "id": BigInteger().primary().autoIncrement(),
        "email": String(255),
        "password": String(255),
        "active": Boolean().nullable(),
    }
    for name, column in columns.items():
        column.name = name
    return TableDefinition(name="accounts", columns=columns, primary_key="id")

def fake_request(session: Session | None) -> SimpleNamespace:
    """Build a request double exposing only ``state.session``."""
    state = SimpleNamespace()
    if session is not None:
        state.session = session
    return SimpleNamespace(state=state)

class _RecordingHasher:
    """Hashing double recording every call made by the provider."""

    __slots__ = ("checked", "hashed")

    def __init__(self) -> None:
        """Start with empty call journals."""
        self.hashed: list[str] = []
        self.checked: list[tuple[str, str]] = []

    def make(self, value: str, **_: object) -> str:
        """Record the hashing of a value and return a marker."""
        self.hashed.append(value)
        return f"hashed:{value}"

    def check(self, value: str, hashed: str) -> bool:
        """Record a verification and answer against the marker."""
        self.checked.append((value, hashed))
        return hashed == f"hashed:{value}"

class _ThreadRecordingProvider:
    """Record the thread performing credential verification."""

    __slots__ = ("thread_id",)

    def __init__(self) -> None:
        """Start without a verification thread."""
        self.thread_id: int | None = None

    async def retrieveByCredentials(self, credentials: object) -> None:
        """Return no identity for the verification probe."""

    def validateCredentials(
        self, identity: object, credentials: object,  # noqa: ARG002
    ) -> bool:
        """Record the executing thread and reject the credentials."""
        self.thread_id = threading.get_ident()
        return False

class _InputRejectingHasher(_RecordingHasher):
    """Model a native password backend rejecting an invalid input value."""

    __slots__ = ()

    def check(self, value: str, hashed: str) -> bool:  # noqa: ARG002
        """Raise a backend input error that must not escape authentication."""
        error_msg = "invalid password input"
        raise ValueError(error_msg)

class TestModelIdentityProvider(TestCase):
    """Validate identity lookup and password verification."""

    async def asyncSetUp(self) -> None:
        """Create the schema and seed a single account."""
        self.app = build_app()
        self.manager = ConnectionManager(self.app)
        self._previous_manager = ConnectionResolver._manager
        ConnectionResolver.setManager(self.manager)
        self.connection = self.manager.connection("sqlite")
        await self.connection.createTable(accounts_table())

        self.hasher = HashManager(self.app)
        self.provider = ModelIdentityProvider(self.app, self.hasher)
        self.hashed = self.hasher.make("secret")
        await Account.create({
            "email": "ada@orionis.dev",
            "password": self.hashed,
            "active": True,
        })

    async def asyncTearDown(self) -> None:
        """Release the SQLite connection."""
        ConnectionResolver.setManager(self._previous_manager)
        await self.connection.disconnect()

    async def testResolvesTheConfiguredModel(self) -> None:
        """Validates that the dotted path in configuration is imported.

        The framework never imports the application identity directly, so
        the provider must resolve and memoise the class itself.
        """
        self.assertIs(self.provider.model(), Account)
        self.assertIs(self.provider.model(), Account)

    async def testRejectsAModelThatIsNotAuthenticatable(self) -> None:
        """Validates that a model without the mixin is refused.

        Accepting it would fail much later, when the guard asks for the
        password hash of an object that cannot answer.
        """
        app = build_app(identity={"model": "orionis.orm.model.Model"})
        provider = ModelIdentityProvider(app, self.hasher)
        with self.assertRaises(IdentityProviderException):
            provider.model()

    async def testRejectsAnUnimportableModel(self) -> None:
        """Validates that a broken dotted path raises a module error.

        The failure must be an authentication error, not a bare
        ``ImportError`` leaking from the framework internals.
        """
        app = build_app(identity={"model": "does.not.exist.Identity"})
        provider = ModelIdentityProvider(app, self.hasher)
        with self.assertRaises(IdentityProviderException):
            provider.model()

    async def testRetrievesAnIdentityByItsIdentifier(self) -> None:
        """Validates the lookup used to restore a session.

        The session only stores the primary key, so the provider must be
        able to rebuild the identity from it.
        """
        identity = await self.provider.retrieveById(1)
        self.assertIsNotNone(identity)
        self.assertEqual(identity.email, "ada@orionis.dev")

    async def testReturnsNoneForAnUnknownIdentifier(self) -> None:
        """Validates that a stale identifier resolves to nothing.

        A deleted account must not keep its session alive.
        """
        self.assertIsNone(await self.provider.retrieveById(999))
        self.assertIsNone(await self.provider.retrieveById(None))

    async def testRetrievesAnIdentityByItsCredentials(self) -> None:
        """Validates that lookup uses the configured username field.

        Only the public credential participates in the lookup; the secret
        is verified separately.
        """
        identity = await self.provider.retrieveByCredentials({
            "email": "ada@orionis.dev",
        })
        self.assertIsNotNone(identity)
        self.assertEqual(identity.getAuthIdentifier(), 1)

    async def testReturnsNoneWhenTheUsernameIsMissing(self) -> None:
        """Validates that an incomplete payload never hits the database.

        A missing or non textual username cannot match anything.
        """
        self.assertIsNone(await self.provider.retrieveByCredentials({}))
        self.assertIsNone(
            await self.provider.retrieveByCredentials({"email": 42}),
        )

    async def testValidatesTheCorrectPassword(self) -> None:
        """Validates that verification delegates to the hashing module.

        Authentication must never compare passwords by hand.
        """
        identity = await self.provider.retrieveById(1)
        granted = self.provider.validateCredentials(
            identity, {"password": "secret"},
        )
        self.assertTrue(granted)

    async def testRejectsAWrongPassword(self) -> None:
        """Validates that a mismatching secret is refused.

        The stored hash must remain the only source of truth.
        """
        identity = await self.provider.retrieveById(1)
        granted = self.provider.validateCredentials(
            identity, {"password": "wrong"},
        )
        self.assertFalse(granted)

    async def testRejectsAnUnknownIdentityWithoutSkippingTheHashing(
        self,
    ) -> None:
        """Validates that a missing identity still burns hashing work.

        Returning early would let an attacker enumerate accounts by
        measuring the response time.
        """
        hasher = _RecordingHasher()
        provider = ModelIdentityProvider(self.app, hasher)

        granted = provider.validateCredentials(None, {"password": "secret"})

        self.assertFalse(granted)
        self.assertEqual(hasher.hashed, ["secret"])
        self.assertEqual(hasher.checked, [])

    async def testRejectsAnEmptyPassword(self) -> None:
        """Validates that a blank secret never reaches the hasher.

        An empty password is a malformed request, not a candidate.
        """
        identity = await self.provider.retrieveById(1)
        self.assertFalse(self.provider.validateCredentials(identity, {}))
        self.assertFalse(
            self.provider.validateCredentials(identity, {"password": ""}),
        )

    async def testBackendInputErrorsAreInvalidCredentials(self) -> None:
        """Deny native backend input errors without exposing password material."""
        identity = await self.provider.retrieveById(1)
        provider = ModelIdentityProvider(self.app, _InputRejectingHasher())
        self.assertFalse(
            provider.validateCredentials(identity, {"password": "invalid"}),
        )
        self.assertFalse(
            provider.validateCredentials(None, {"password": "x" * 5000}),
        )

class TestSessionGuard(TestCase):
    """Validate the web authentication lifecycle."""

    async def asyncSetUp(self) -> None:
        """Create the schema, seed an account and build the guard."""
        self.app = build_app()
        self.manager = ConnectionManager(self.app)
        self._previous_manager = ConnectionResolver._manager
        ConnectionResolver.setManager(self.manager)
        self.connection = self.manager.connection("sqlite")
        await self.connection.createTable(accounts_table())

        self.hasher = HashManager(self.app)
        self.provider = ModelIdentityProvider(self.app, self.hasher)
        self.guard = SessionGuard(self.app, self.provider)
        await Account.create({
            "email": "ada@orionis.dev",
            "password": self.hasher.make("secret"),
            "active": True,
        })

    async def asyncTearDown(self) -> None:
        """Release the SQLite connection."""
        ConnectionResolver.setManager(self._previous_manager)
        await self.connection.disconnect()

    async def testExposesItsConfigurationName(self) -> None:
        """Validates the name used to select the guard.

        The manager resolves guards by this exact string.
        """
        self.assertEqual(self.guard.name, "session")

    async def testAttemptAuthenticatesValidCredentials(self) -> None:
        """Validates the happy path of a web login.

        The identity is returned and remembered in the session.
        """
        session = Session()
        request = fake_request(session)

        identity = await self.guard.attempt(
            request, {"email": "ada@orionis.dev", "password": "secret"},
        )

        self.assertIsNotNone(identity)
        self.assertEqual(session.get("_auth_identifier"), "1")

    async def testAttemptRotatesTheSessionIdentifier(self) -> None:
        """Validates the protection against session fixation.

        A value planted before the login must stop being valid.
        """
        session = Session()
        session.put("planted", "value")
        self.assertFalse(session.wantsRegenerate)

        await self.guard.attempt(
            fake_request(session),
            {"email": "ada@orionis.dev", "password": "secret"},
        )

        self.assertTrue(session.wantsRegenerate)

    async def testAttemptRejectsAWrongPassword(self) -> None:
        """Validates that a bad secret leaves the session anonymous.

        Nothing must be written when the credentials do not match.
        """
        session = Session()
        identity = await self.guard.attempt(
            fake_request(session),
            {"email": "ada@orionis.dev", "password": "wrong"},
        )

        self.assertIsNone(identity)
        self.assertIsNone(session.get("_auth_identifier"))

    async def testAttemptRejectsAnUnknownIdentity(self) -> None:
        """Validates that a missing account is refused like a bad secret.

        The caller cannot tell the two failures apart.
        """
        session = Session()
        identity = await self.guard.attempt(
            fake_request(session),
            {"email": "ghost@orionis.dev", "password": "secret"},
        )

        self.assertIsNone(identity)
        self.assertIsNone(session.get("_auth_identifier"))

    async def testResolveRestoresTheIdentityFromTheSession(self) -> None:
        """Validates the per request restoration of a logged in user.

        Only the identifier travels in the session; the row is reloaded.
        """
        session = Session()
        session.put("_auth_identifier", 1)

        result = await self.guard.resolve(fake_request(session))

        self.assertIsNotNone(result)
        self.assertEqual(result.guard, "session")
        self.assertEqual(result.identity.getAuthIdentifier(), 1)
        self.assertIsNone(result.abilities)

    async def testResolveReturnsNoneWithoutSession(self) -> None:
        """Validates that API routes without a session stay anonymous.

        The guard must not explode outside the web pipeline.
        """
        self.assertIsNone(await self.guard.resolve(fake_request(None)))

    async def testResolveReturnsNoneForAnEmptySession(self) -> None:
        """Validates that a fresh visitor is a guest.

        No identifier means nothing to restore.
        """
        self.assertIsNone(await self.guard.resolve(fake_request(Session())))

    async def testResolveCleansUpAStaleIdentifier(self) -> None:
        """Validates that a deleted account clears the session key.

        Leaving the key would retry the same failing lookup forever.
        """
        session = Session()
        session.put("_auth_identifier", 999)

        result = await self.guard.resolve(fake_request(session))

        self.assertIsNone(result)
        self.assertIsNone(session.get("_auth_identifier"))

    async def testLoginRequiresASession(self) -> None:
        """Validates that logging in without a session fails loudly.

        Silently doing nothing would look like a successful login.
        """
        identity = await self.provider.retrieveById(1)
        with self.assertRaises(AuthException):
            self.guard.login(fake_request(None), identity)

    async def testLogoutInvalidatesTheSession(self) -> None:
        """Validates that logging out destroys the session entirely.

        Only forgetting the key would leave the rest of the payload alive.
        """
        session = Session()
        session.put("_auth_identifier", 1)
        session.put("cart", ["book"])

        self.guard.logout(fake_request(session))

        self.assertTrue(session.invalidated)
        self.assertEqual(session.all(), {})

    async def testLogoutWithoutSessionIsANoOperation(self) -> None:
        """Validates that logging out is safe outside the web pipeline.

        A request without a session is already anonymous.
        """
        self.guard.logout(fake_request(None))

    async def testPasswordVerificationRunsOutsideTheEventLoopThread(self) -> None:
        """Keep expensive password verification off the HTTP event loop."""
        provider = _ThreadRecordingProvider()
        guard = SessionGuard(self.app, provider)
        await guard.attempt(fake_request(Session()), {})
        self.assertIsNotNone(provider.thread_id)
        self.assertNotEqual(provider.thread_id, threading.get_ident())

    async def testLoginRotatesCsrfAndPreservesUnrelatedSessionData(self) -> None:
        """Rotate security credentials without losing the visitor's payload."""
        identity = await self.provider.retrieveById(1)
        session = Session()
        previous = "previous-csrf-value"
        session.put("_csrf_token", previous)
        session.put("cart", ["book"])
        request = fake_request(session)
        self.guard.login(request, identity)
        self.assertNotEqual(session.get("_csrf_token"), previous)
        self.assertEqual(request.state.csrf_token, session.get("_csrf_token"))
        self.assertEqual(session.get("cart"), ["book"])

    def testLoginRejectsAnUnsavedIdentity(self) -> None:
        """Never authenticate a model whose primary key has not been assigned."""
        with self.assertRaises(AuthException):
            self.guard.login(fake_request(Session()), Account())
