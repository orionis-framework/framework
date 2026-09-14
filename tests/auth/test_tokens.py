import asyncio
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from orionis.auth.exceptions import TokenException
from orionis.auth.guards.token_guard import TokenGuard
from orionis.auth.tokens import repository as token_module
from orionis.auth.tokens.functions import generate_token_secret, hash_token_secret
from orionis.auth.tokens.repository import AccessTokenRepository
from orionis.database.connection_manager import ConnectionManager
from orionis.database.compiler import SQLCompiler
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, DateTime, String, Text
from orionis.test import TestCase

class _StubApp:
    """Application stub exposing the database and token configuration."""

    __slots__ = ("_database", "_tokens")

    def __init__(self, database: str, tokens: dict[str, Any] | None = None) -> None:
        """Store the database path and the token options."""
        self._database = database
        self._tokens = tokens or {}

    def config(self, key: str | None = None) -> Any:  # noqa: ANN401
        """Resolve a dot-notated configuration key."""
        tree: dict[str, Any] = {
            "database": {
                "default": "sqlite",
                "connections": {
                    "sqlite": {
                        "driver": "sqlite",
                        "database": self._database,
                        "prefix": "",
                    },
                },
            },
            "auth": {"tokens": self._tokens},
        }
        if key is None:
            return tree
        node: Any = tree
        for part in key.split("."):
            if not isinstance(node, dict):
                return None
            node = node.get(part)
            if node is None:
                return None
        return node

class _Identity:
    """Authorizable double owning personal access tokens."""

    __slots__ = ("identifier", "kind")

    def __init__(self, identifier: int, kind: str = "tests.Account") -> None:
        """Store the polymorphic type and the identifier."""
        self.identifier = identifier
        self.kind = kind

    def getAuthIdentifierName(self) -> str:
        """Return the attribute holding the identifier."""
        return "identifier"

    def getAuthIdentifier(self) -> object:
        """Return the identifier of this identity."""
        return self.identifier

    def getAuthPassword(self) -> str:
        """Return an empty hash; tokens never use passwords."""
        return ""

    def getAuthorizableType(self) -> str:
        """Return the polymorphic type of this identity."""
        return self.kind

    def getAuthorizableId(self) -> object:
        """Return the identifier stored in the token row."""
        return self.identifier

class _DirectoryProvider:
    """Identity provider double backed by an in-memory mapping."""

    __slots__ = ("entered", "identities", "released")

    def __init__(self, identities: dict[int, _Identity]) -> None:
        """Store the identities this provider can resolve."""
        self.identities = identities
        self.entered: asyncio.Event | None = None
        self.released: asyncio.Event | None = None

    async def retrieveById(self, identifier: object) -> _Identity | None:
        """Return the identity registered under the identifier."""
        if self.entered is not None and self.released is not None:
            self.entered.set()
            await self.released.wait()
        return self.identities.get(int(identifier))

    async def retrieveByCredentials(self, credentials: object) -> _Identity | None:  # noqa: ARG002
        """Credential lookup is never used by the token guard."""
        return None

    def validateCredentials(self, identity: object, credentials: object) -> bool:  # noqa: ARG002
        """Credential verification is never used by the token guard."""
        return False

def tokens_table() -> TableDefinition:
    """Build the ``personal_access_tokens`` table used by the tests."""
    columns = {
        "id": BigInteger().primary().autoIncrement(),
        "tokenable_type": String(255),
        "tokenable_id": String(255),
        "name": String(255),
        "token": String(64).unique(),
        "abilities": Text().nullable(),
        "last_used_at": DateTime().nullable(),
        "expires_at": DateTime().nullable(),
        "revoked_at": DateTime().nullable(),
        "created_at": DateTime().nullable(),
        "updated_at": DateTime().nullable(),
    }
    for name, column in columns.items():
        column.name = name
    return TableDefinition(
        name="personal_access_tokens",
        columns=columns,
        primary_key="id",
    )

def bearer_request(token: str | None) -> SimpleNamespace:
    """Build a request double exposing only the bearer token."""
    return SimpleNamespace(bearerToken=token)

class TestTokenFunctions(TestCase):
    """Validate the primitives backing personal access tokens."""

    def testSecretsAreUniqueAndUrlSafe(self) -> None:
        """Validates that generated secrets never repeat.

        Reusing a secret would let one client impersonate another.
        """
        secrets_seen = {generate_token_secret(40) for _ in range(200)}
        self.assertEqual(len(secrets_seen), 200)
        for secret in secrets_seen:
            self.assertNotIn("|", secret)
            self.assertNotIn(" ", secret)

    def testSecretLengthFollowsTheRequestedEntropy(self) -> None:
        """Validates that the configured entropy reaches the generator.

        More random bytes must produce a longer token.
        """
        short = generate_token_secret(32)
        long = generate_token_secret(64)
        self.assertLess(len(short), len(long))

    def testDigestIsStableAndFixedWidth(self) -> None:
        """Validates the value persisted in the database.

        The digest must be deterministic so lookups are a single index
        hit, and always 64 hexadecimal characters wide.
        """
        digest = hash_token_secret("a-secret")
        self.assertEqual(digest, hash_token_secret("a-secret"))
        self.assertEqual(len(digest), 64)
        self.assertNotEqual(digest, hash_token_secret("another-secret"))

class _TokenCase(TestCase):
    """Base case creating the token table on a temporary SQLite file."""

    tokens_config: dict[str, Any] = {}  # noqa: RUF012

    async def asyncSetUp(self) -> None:
        """Create the schema and build the repository."""
        self._tmp = tempfile.TemporaryDirectory()
        database = str(Path(self._tmp.name) / "tokens.sqlite")

        self.app = _StubApp(database, self.tokens_config)
        self.manager = ConnectionManager(self.app)
        self._previous_manager = ConnectionResolver._manager
        ConnectionResolver.setManager(self.manager)
        self.connection = self.manager.connection("sqlite")
        await self.connection.createTable(tokens_table())

        self.db = QueryBuilder(self.manager)
        self.repository = AccessTokenRepository(self.app, self.db)
        self.identity = _Identity(1)

    async def asyncTearDown(self) -> None:
        """Release the connection and drop the temporary database."""
        ConnectionResolver.setManager(self._previous_manager)
        await self.connection.disconnect()
        self._tmp.cleanup()

class TestAccessTokenRepository(_TokenCase):
    """Validate the persistence of personal access tokens."""

    async def testIssuesATokenAndStoresOnlyItsDigest(self) -> None:
        """Validates the core security property of opaque tokens.

        A leaked database row must never expose a usable credential.
        """
        issued = await self.repository.create(self.identity, "ci")

        row = await self.db.table("personal_access_tokens").first()
        self.assertNotEqual(row["token"], issued.plain_text)
        self.assertEqual(row["token"], hash_token_secret(issued.plain_text))
        self.assertEqual(row["tokenable_type"], "tests.Account")
        self.assertEqual(row["tokenable_id"], "1")
        self.assertEqual(issued.access_token.name, "ci")

    async def testTheseSecretNeverAppearsInTheRepresentation(self) -> None:
        """Validates that the plain text stays out of debugging output.

        A token printed in a log would be a credential leak.
        """
        issued = await self.repository.create(self.identity, "ci")
        self.assertNotIn(issued.plain_text, repr(issued))
        self.assertNotIn(issued.plain_text, str(issued.toDict()))
        self.assertNotIn("plain_text", issued.toDict())
        self.assertFalse(hasattr(issued, "__dict__"))
        self.assertFalse(hasattr(issued.access_token, "__dict__"))

    async def testRejectsAnEmptyName(self) -> None:
        """Validates the only input guard of token creation.

        A nameless token cannot be audited nor revoked with confidence.
        """
        with self.assertRaises(TokenException):
            await self.repository.create(self.identity, "   ")

    async def testResolvesAValidToken(self) -> None:
        """Validates the lookup performed on every API request.

        The presented value is hashed and matched against the index.
        """
        issued = await self.repository.create(self.identity, "ci")

        found = await self.repository.findByPlainText(issued.plain_text)

        self.assertIsNotNone(found)
        self.assertEqual(found.id, issued.access_token.id)
        self.assertEqual(found.tokenable_id, "1")
        self.assertIsNone(found.abilities)

    async def testRejectsAnUnknownToken(self) -> None:
        """Validates that a forged value resolves to nothing.

        Every failure mode answers exactly the same way.
        """
        self.assertIsNone(await self.repository.findByPlainText("forged"))
        self.assertIsNone(await self.repository.findByPlainText(""))

    async def testStoresAndRestoresTheAbilities(self) -> None:
        """Validates the round trip of the token restrictions.

        Abilities must survive the JSON encoding used for storage.
        """
        issued = await self.repository.create(
            self.identity, "reader", abilities=["users.view", "users.list"],
        )

        found = await self.repository.findByPlainText(issued.plain_text)

        self.assertEqual(
            found.abilities, frozenset({"users.view", "users.list"}),
        )

    async def testAnEmptyAbilitySetIsPreserved(self) -> None:
        """Validates that "no ability" differs from "unrestricted".

        Collapsing both would silently widen the token.
        """
        issued = await self.repository.create(
            self.identity, "powerless", abilities=[],
        )

        found = await self.repository.findByPlainText(issued.plain_text)

        self.assertEqual(found.abilities, frozenset())

    async def testRejectsAnExpiredToken(self) -> None:
        """Validates that expiration is honoured on lookup.

        An expired token is indistinguishable from an unknown one.
        """
        issued = await self.repository.create(
            self.identity,
            "stale",
            expires_at=datetime.now(UTC).replace(tzinfo=None)
            - timedelta(minutes=1),
        )

        self.assertIsNone(
            await self.repository.findByPlainText(issued.plain_text),
        )

    async def testAcceptsATokenThatHasNotExpiredYet(self) -> None:
        """Validates the boundary of the expiration check.

        A token valid for another hour must keep working.
        """
        issued = await self.repository.create(
            self.identity,
            "fresh",
            expires_at=datetime.now(UTC).replace(tzinfo=None)
            + timedelta(hours=1),
        )

        self.assertIsNotNone(
            await self.repository.findByPlainText(issued.plain_text),
        )

    async def testRevokedTokensStopBeingAccepted(self) -> None:
        """Validates immediate revocation.

        Opaque tokens are chosen precisely so revocation is instant.
        """
        issued = await self.repository.create(self.identity, "ci")

        revoked = await self.repository.revoke(issued.access_token.id)

        self.assertTrue(revoked)
        self.assertIsNone(
            await self.repository.findByPlainText(issued.plain_text),
        )

    async def testRevokingTwiceReportsNoFurtherChange(self) -> None:
        """Validates that revocation is idempotent.

        Only the call that actually revoked reports success.
        """
        issued = await self.repository.create(self.identity, "ci")

        self.assertTrue(await self.repository.revoke(issued.access_token.id))
        self.assertFalse(await self.repository.revoke(issued.access_token.id))
        self.assertFalse(await self.repository.revoke(None))

    async def testRevokesEveryTokenOfAnIdentity(self) -> None:
        """Validates the bulk revocation used on password changes.

        Only the tokens of that identity may be affected.
        """
        other = _Identity(2)
        await self.repository.create(self.identity, "one")
        await self.repository.create(self.identity, "two")
        kept = await self.repository.create(other, "kept")

        revoked = await self.repository.revokeAll(self.identity)

        self.assertEqual(revoked, 2)
        self.assertIsNotNone(
            await self.repository.findByPlainText(kept.plain_text),
        )

    async def testSupportsSeveralTokensPerIdentity(self) -> None:
        """Validates that an identity may hold many credentials.

        Each device or integration gets its own revocable token.
        """
        first = await self.repository.create(self.identity, "laptop")
        second = await self.repository.create(self.identity, "phone")

        self.assertNotEqual(first.plain_text, second.plain_text)
        self.assertIsNotNone(
            await self.repository.findByPlainText(first.plain_text),
        )
        self.assertIsNotNone(
            await self.repository.findByPlainText(second.plain_text),
        )

    async def testRecordsTheLastUsage(self) -> None:
        """Validates the audit trail of a token.

        The column starts empty and is filled by a single statement.
        """
        issued = await self.repository.create(self.identity, "ci")
        self.assertIsNone(issued.access_token.last_used_at)

        await self.repository.touch(issued.access_token.id)

        row = await self.db.table("personal_access_tokens").first()
        self.assertIsNotNone(row["last_used_at"])

    async def testTouchingAnUnknownTokenIsSafe(self) -> None:
        """Validates the no-op path of the usage update.

        A missing identifier must not raise.
        """
        await self.repository.touch(None)

    async def testPurgesExpiredAndRevokedTokens(self) -> None:
        """Validates the maintenance operation.

        Only unusable rows may be deleted.
        """
        alive = await self.repository.create(self.identity, "alive")
        expired = await self.repository.create(
            self.identity,
            "expired",
            expires_at=datetime.now(UTC).replace(tzinfo=None)
            - timedelta(minutes=1),
        )
        revoked = await self.repository.create(self.identity, "revoked")
        await self.repository.revoke(revoked.access_token.id)

        removed = await self.repository.purgeExpired()

        self.assertEqual(removed, 2)
        rows = await self.db.table("personal_access_tokens").get()
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(
            await self.repository.findByPlainText(alive.plain_text),
        )
        self.assertIsNone(
            await self.repository.findByPlainText(expired.plain_text),
        )

    async def testCorruptRestrictionsNeverBecomeUnrestricted(self) -> None:
        """Reject corrupt abilities and timestamps instead of widening access."""
        for field, value in (
            ("abilities", "invalid-json"),
            ("abilities", "null"),
            ("abilities", '{"users.delete": true}'),
            ("abilities", '[1, "users.view"]'),
        ):
            issued = await self.repository.create(self.identity, "corrupt")
            await (
                self.db.table("personal_access_tokens")
                .where("id", issued.access_token.id)
                .update({field: value})
            )
            self.assertIsNone(
                await self.repository.findByPlainText(issued.plain_text),
            )

    def testMalformedStoredTimestampIsRejected(self) -> None:
        """Reject malformed dates from schemaless drivers at the parser boundary."""
        with self.assertRaises(TokenException):
            token_module._as_datetime("not-a-date")

    async def testRejectsMalformedAbilityInputs(self) -> None:
        """Reject strings and non-string abilities at the issuance boundary."""
        for abilities in ("users.view", [1], [""], [{}]):
            with self.assertRaises(TokenException):
                await self.repository.create(
                    self.identity, "invalid", abilities=abilities,
                )

    async def testConcurrentCreationKeepsEveryCredentialIndependent(self) -> None:
        """Persist all concurrent tokens with unique secrets and row IDs."""
        issued = await asyncio.gather(*(
            self.repository.create(self.identity, f"client-{index}")
            for index in range(12)
        ))
        self.assertEqual(len({item.plain_text for item in issued}), 12)
        self.assertEqual(len({item.access_token.id for item in issued}), 12)
        self.assertEqual(await self.db.table("personal_access_tokens").count(), 12)

    async def testConcurrentRevocationHasOneWinner(self) -> None:
        """Allow only one revoker to change an active token."""
        issued = await self.repository.create(self.identity, "shared")
        results = await asyncio.gather(*(
            self.repository.revoke(issued.access_token.id) for _ in range(8)
        ))
        self.assertEqual(results.count(True), 1)
        self.assertFalse(await self.repository.touch(issued.access_token.id))

    async def testIssuanceWorksWithoutCachedSchemaMetadata(self) -> None:
        """Recover the token ID after a process restart with a schemaless builder."""
        self.connection._compiler = SQLCompiler()
        issued = await self.repository.create(self.identity, "cold")
        self.assertIsNotNone(issued.access_token.id)
        self.assertTrue(await self.repository.revoke(issued.access_token.id))

class TestConfiguredTokenExpiration(_TokenCase):
    """Validate the default lifetime configured for new tokens."""

    tokens_config = {"expiration": 60}  # noqa: RUF012

    async def testAppliesTheConfiguredLifetime(self) -> None:
        """Validates that tokens expire without an explicit deadline.

        The configuration is the single source of truth for the default.
        """
        issued = await self.repository.create(self.identity, "ci")

        self.assertIsNotNone(issued.access_token.expires_at)
        row = await self.db.table("personal_access_tokens").first()
        self.assertIsNotNone(row["expires_at"])

    async def testAnExplicitDeadlineWinsOverTheConfiguration(self) -> None:
        """Validates that a caller may shorten or extend the lifetime.

        The explicit value must not be overwritten by the default.
        """
        deadline = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)

        issued = await self.repository.create(
            self.identity, "long", expires_at=deadline,
        )

        self.assertEqual(issued.access_token.expires_at, deadline)

class TestTokenGuard(_TokenCase):
    """Validate how API requests are authenticated."""

    async def asyncSetUp(self) -> None:
        """Build the guard on top of the token repository."""
        await super().asyncSetUp()
        self.provider = _DirectoryProvider({1: self.identity})
        self.guard = TokenGuard(self.repository, self.provider)

    async def testExposesItsConfigurationName(self) -> None:
        """Validates the name used to select the guard.

        The manager resolves guards by this exact string.
        """
        self.assertEqual(self.guard.name, "token")

    async def testResolvesTheIdentityOwningTheToken(self) -> None:
        """Validates the happy path of API authentication.

        The abilities of the token travel with the result.
        """
        issued = await self.repository.create(
            self.identity, "ci", abilities=["users.view"],
        )

        result = await self.guard.resolve(bearer_request(issued.plain_text))

        self.assertIsNotNone(result)
        self.assertEqual(result.guard, "token")
        self.assertIs(result.identity, self.identity)
        self.assertEqual(result.abilities, frozenset({"users.view"}))
        self.assertEqual(result.credential_id, issued.access_token.id)

    async def testMarksTheTokenAsUsed(self) -> None:
        """Validates that a successful request updates the audit column.

        This is the only write a read-only API request performs.
        """
        issued = await self.repository.create(self.identity, "ci")

        await self.guard.resolve(bearer_request(issued.plain_text))

        row = await self.db.table("personal_access_tokens").first()
        self.assertIsNotNone(row["last_used_at"])

    async def testRequestsWithoutATokenStayAnonymous(self) -> None:
        """Validates that a missing header is not an error.

        Public API routes must keep working.
        """
        self.assertIsNone(await self.guard.resolve(bearer_request(None)))
        self.assertIsNone(await self.guard.resolve(bearer_request("")))

    async def testUnknownRevokedAndExpiredTokensAreRefused(self) -> None:
        """Validates that every unusable token answers the same way.

        The client cannot tell why the credential was rejected.
        """
        revoked = await self.repository.create(self.identity, "revoked")
        await self.repository.revoke(revoked.access_token.id)
        expired = await self.repository.create(
            self.identity,
            "expired",
            expires_at=datetime.now(UTC).replace(tzinfo=None)
            - timedelta(minutes=1),
        )

        self.assertIsNone(await self.guard.resolve(bearer_request("forged")))
        self.assertIsNone(
            await self.guard.resolve(bearer_request(revoked.plain_text)),
        )
        self.assertIsNone(
            await self.guard.resolve(bearer_request(expired.plain_text)),
        )

    async def testRefusesATokenWhoseOwnerDisappeared(self) -> None:
        """Validates that deleting an account invalidates its tokens.

        The identity provider is the source of truth.
        """
        ghost = _Identity(99)
        issued = await self.repository.create(ghost, "ghost")

        self.assertIsNone(
            await self.guard.resolve(bearer_request(issued.plain_text)),
        )

    async def testRevocationDuringIdentityLookupPreventsAuthentication(self) -> None:
        """Recheck token validity after the identity provider has suspended."""
        issued = await self.repository.create(self.identity, "racing")
        self.provider.entered = asyncio.Event()
        self.provider.released = asyncio.Event()
        pending = asyncio.create_task(
            self.guard.resolve(bearer_request(issued.plain_text)),
        )
        await self.provider.entered.wait()
        try:
            await self.repository.revoke(issued.access_token.id)
        finally:
            self.provider.released.set()
        self.assertIsNone(await pending)

    async def testMismatchedIdentityIdentifierIsRefused(self) -> None:
        """Refuse a provider response that belongs to a different owner."""
        issued = await self.repository.create(self.identity, "account")
        self.provider.identities[1] = _Identity(2)
        self.assertIsNone(
            await self.guard.resolve(bearer_request(issued.plain_text)),
        )

    async def testRefusesATokenIssuedForAnotherKindOfOwner(self) -> None:
        """Validates the polymorphic guard on the token row.

        A token minted for a team must not authenticate an account.
        """
        issued = await self.repository.create(
            _Identity(1, "tests.Team"), "team",
        )

        self.assertIsNone(
            await self.guard.resolve(bearer_request(issued.plain_text)),
        )
