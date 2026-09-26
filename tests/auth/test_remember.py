import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from database.migrations import (
    m0000000012_create_password_reset_tokens_table as reset_migration,
)
from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.exceptions import AuthException
from orionis.auth.guards.session_guard import SessionGuard
from orionis.auth.identity.provider import ModelIdentityProvider
from orionis.auth.middleware.resolve_identity import ResolveSessionIdentityMiddleware
from orionis.auth.passwords.broker import PasswordBroker
from orionis.auth.remember import RememberMe, apply_remember_cookie
from orionis.container.context.manager import ScopeManager
from orionis.database.connection_manager import ConnectionManager
from orionis.database.schema.schema import Schema as DatabaseSchema
from orionis.foundation.config.auth import RememberAuth
from orionis.hashing.hash_manager import HashManager
from orionis.http.default.controllers.login_controller import LoginController
from orionis.http.responses import Response
from orionis.http.payload.estructures.cookies import Cookies
from orionis.orm import BigInteger, Boolean, Model, String
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.session.session import Session
from orionis.test import TestCase
from tests.auth.test_identity_and_session import build_app


class RememberAccount(Model, Authenticatable):
    """Use the same persistent credential column declared in the app migration."""

    table = "remember_accounts"
    timestamps = False
    id = BigInteger().primary().autoIncrement()
    email = String(255).unique()
    password = String(255)
    active = Boolean()
    remember_token = String(100).nullable()


def request(cookie: str | None = None, *, scheme: str = "https") -> SimpleNamespace:
    """Create an independent browser session with an optional remembered login."""
    return SimpleNamespace(
        scheme=scheme,
        state=SimpleNamespace(session=Session()),
        cookies={} if cookie is None else {"orionis_remember": cookie},
    )


def queued_cookie(incoming: SimpleNamespace) -> str:
    """Read the raw cookie only inside a test, never in application logs."""
    return incoming.state._auth_remember_cookie["value"]


class TestRememberMe(TestCase):
    """Exercise real database updates and token races without live browser data."""

    async def asyncSetUp(self) -> None:
        """Create a temporary database and an account with a real password hash."""
        self.temp = tempfile.TemporaryDirectory()
        self.app = build_app(identity={"model": f"{__name__}.RememberAccount"})
        self.app._config["database"]["connections"]["sqlite"]["database"] = str(
            Path(self.temp.name) / "remember.sqlite",
        )
        self.manager = ConnectionManager(self.app)
        self.previous_manager = ConnectionResolver._manager
        ConnectionResolver.setManager(self.manager)
        self.connection = self.manager.connection("sqlite")
        await self.connection.createTable(RememberAccount.__meta__.table)
        self.hashing = HashManager(self.app)
        self.identities = ModelIdentityProvider(self.app, self.hashing)
        self.guard = SessionGuard(self.app, self.identities)
        self.remember = RememberMe(self.app, self.identities)
        self.user = await RememberAccount.create(
            {
                "email": "ada@example.com",
                "password": await self.hashing.make("Secret1!"),
                "active": True,
            },
        )

    async def asyncTearDown(self) -> None:
        """Release the temporary connection and restore the test resolver."""
        ConnectionResolver.setManager(self.previous_manager)
        await self.connection.disconnect()
        self.temp.cleanup()

    async def login(self, *, remember: bool = True) -> SimpleNamespace:
        """Submit verified credentials through the real session guard."""
        incoming = request()
        result = await self.guard.attempt(
            incoming,
            {
                "email": self.user.email,
                "password": "Secret1!",
            },
            remember=remember,
        )
        self.assertIsNotNone(result)
        return incoming

    async def testOptInStoresOnlyDigestAndUsesSecureCookie(self) -> None:
        """Issue a bounded, HttpOnly credential only after password verification."""
        incoming = await self.login()
        cookie = queued_cookie(incoming)
        stored = (await RememberAccount.find(self.user.id)).remember_token
        self.assertTrue(stored.startswith("v1:"))
        self.assertLessEqual(len(stored), 100)
        self.assertNotIn(cookie.rsplit("|", 1)[1], stored)
        outgoing = Response()
        apply_remember_cookie(incoming, outgoing)
        header = outgoing.getHeader("set-cookie")[0]
        self.assertIn("HttpOnly", header)
        self.assertIn("Secure", header)
        self.assertIn("SameSite=lax", header)
        self.assertIn("Path=/", header)
        self.assertNotIn("Domain=", header)
        self.assertIn("Max-Age=2592000", header)
        self.assertEqual(outgoing.getHeader("cache-control"), ["no-store"])

    async def testRestoreRotatesCredentialAndCreatesFreshSession(self) -> None:
        """Persistent login renews both the bearer token and session CSRF token."""
        original = queued_cookie(await self.login())
        incoming = request(original)
        incoming.state.session.put("_csrf_token", "old-csrf")
        result = await self.guard.resolve(incoming)
        self.assertEqual(result.identity.id, self.user.id)
        replacement = queued_cookie(incoming)
        self.assertNotEqual(original, replacement)
        self.assertEqual(original.split("|")[1], replacement.split("|")[1])
        self.assertTrue(incoming.state.session.wantsRegenerate)
        self.assertNotEqual(incoming.state.session.get("_csrf_token"), "old-csrf")
        self.assertIsNone(await self.guard.resolve(request(original)))
        self.assertIsNotNone(await self.guard.resolve(request(replacement)))

    async def testWebMiddlewareRestoresEncodedCookieAndReturnsReplacement(self) -> None:
        """Exercise the response hook and the browser's percent-encoded cookie."""
        logged_in = await self.login()
        response = Response()
        apply_remember_cookie(logged_in, response)
        incoming = request()
        incoming.cookies = Cookies(response.getHeader("set-cookie")[0].split(";", 1)[0])
        middleware = ResolveSessionIdentityMiddleware(
            SimpleNamespace(guard=lambda _: self.guard),
            None,
        )

        async def endpoint():
            self.assertEqual(
                incoming.state.session.get("_auth_identifier"), str(self.user.id),
            )
            return Response("authenticated")

        async with ScopeManager():
            result = await middleware.handle(incoming, endpoint)
        self.assertTrue(result.hasHeader("set-cookie"))
        self.assertIn("HttpOnly", result.getHeader("set-cookie")[0])
        self.assertNotEqual(queued_cookie(incoming), queued_cookie(logged_in))

    async def testWrongPasswordNeverIssuesPersistentCredential(self) -> None:
        """A submitted opt-in flag cannot bypass password verification."""
        incoming = request()
        self.assertIsNone(
            await self.guard.attempt(
                incoming,
                {
                    "email": self.user.email,
                    "password": "Wrong1!",
                },
                remember=True,
            ),
        )
        self.assertFalse(hasattr(incoming.state, "_auth_remember_cookie"))
        self.assertIsNone((await RememberAccount.find(self.user.id)).remember_token)

    async def testOptOutRevokesExistingRememberedLogin(self) -> None:
        """A subsequent login without opt-in removes the previous credential."""
        original = queued_cookie(await self.login())
        incoming = await self.login(remember=False)
        self.assertEqual(queued_cookie(incoming), "")
        self.assertIsNone((await RememberAccount.find(self.user.id)).remember_token)
        self.assertIsNone(await self.guard.resolve(request(original)))

    async def testLogoutRevokesCookieAndServerToken(self) -> None:
        """A stolen pre-logout cookie cannot silently create another session."""
        incoming = await self.login()
        original = queued_cookie(incoming)
        await self.guard.logout(incoming)
        self.assertTrue(incoming.state.session.invalidated)
        self.assertIsNone((await RememberAccount.find(self.user.id)).remember_token)
        self.assertEqual(incoming.state._auth_remember_cookie["max_age"], 0)
        self.assertIsNone(await self.guard.resolve(request(original)))

    async def testLogoutAfterRestoreRevokesRotatedToken(self) -> None:
        """Logout reads the fresh database token after restoration has rotated it."""
        incoming = request(queued_cookie(await self.login()))
        await self.guard.resolve(incoming)
        rotated = queued_cookie(incoming)
        await self.guard.logout(incoming)
        self.assertIsNone(await self.guard.resolve(request(rotated)))

    async def testNewOptInReplacesPreviousDevice(self) -> None:
        """The single database column deliberately keeps only the newest grant."""
        original = queued_cookie(await self.login())
        newest = queued_cookie(await self.login())
        self.assertIsNone(await self.guard.resolve(request(original)))
        self.assertIsNotNone(await self.guard.resolve(request(newest)))

    async def testTamperedCookieCannotSelectAnotherUserOrExtendExpiry(self) -> None:
        """Public selectors and timestamps are bound to the stored digest."""
        original = queued_cookie(await self.login())
        identifier, expiry, secret = original.split("|")
        for value in (
            f"99|{expiry}|{secret}",
            f"{identifier}|{int(expiry) + 60}|{secret}",
            f"{identifier}|{expiry}|{'x' * 43}",
            "malformed",
            "x" * 513,
        ):
            with self.subTest(value=value):
                self.assertIsNone(await self.guard.resolve(request(value)))

    async def testExpiredCookieIsRejectedAtServerEvenIfBrowserKeepsIt(self) -> None:
        """Expiration is enforced independently of the client's Max-Age handling."""
        original = queued_cookie(await self.login())
        expiry = int(original.split("|")[1])
        with patch("orionis.auth.remember.time.time", return_value=expiry):
            incoming = request(original)
            self.assertIsNone(await self.guard.resolve(incoming))
        self.assertEqual(queued_cookie(incoming), "")

    async def testInactiveDeletedAndPasswordChangedAccountsCannotRestore(self) -> None:
        """A valid cookie does not override current account state or credentials."""
        original = queued_cookie(await self.login())
        await (
            RememberAccount.query().where("id", self.user.id).update({"active": False})
        )
        self.assertIsNone(await self.guard.resolve(request(original)))
        await (
            RememberAccount.query()
            .where("id", self.user.id)
            .update(
                {
                    "active": True,
                    "password": await self.hashing.make("Changed1!"),
                },
            )
        )
        self.assertIsNone(await self.guard.resolve(request(original)))
        await RememberAccount.query().where("id", self.user.id).delete()
        self.assertIsNone(await self.guard.resolve(request(original)))

    async def testConcurrentRestorationHasOneWinner(self) -> None:
        """Only one request can exchange a token, without erasing its replacement."""
        original = queued_cookie(await self.login())
        incoming = [request(original) for _ in range(5)]
        results = await asyncio.gather(*(self.guard.resolve(item) for item in incoming))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(
            sum(hasattr(item.state, "_auth_remember_cookie") for item in incoming),
            1,
        )

    async def testSecureModeRejectsHttpWithoutAuthenticating(self) -> None:
        """A misconfigured HTTP deployment cannot accidentally issue a bearer cookie."""
        incoming = request(scheme="http")
        with self.assertRaises(AuthException):
            await self.guard.attempt(
                incoming,
                {
                    "email": self.user.email,
                    "password": "Secret1!",
                },
                remember=True,
            )
        self.assertIsNone(incoming.state.session.get("_auth_identifier"))
        original = queued_cookie(await self.login())
        self.assertIsNone(await self.guard.resolve(request(original, scheme="http")))

    async def testPasswordResetClearsRememberToken(self) -> None:
        """The reset broker revokes persistent login in its password transaction."""
        original = queued_cookie(await self.login())
        with patch.object(reset_migration, "Schema", DatabaseSchema(self.manager)):
            await reset_migration.CreatePasswordResetTokensTable().up()
        broker = PasswordBroker(self.app, QueryBuilder(self.manager), self.hashing)
        _, token = await broker.issue(self.user.email)
        self.assertIsNotNone(
            await broker.reset(self.user.email, token, "NewPassword1!"),
        )
        self.assertIsNone((await RememberAccount.find(self.user.id)).remember_token)
        self.assertIsNone(await self.guard.resolve(request(original)))


class TestRememberConfigurationAndController(TestCase):
    """Verify opt-in wiring and the configuration's safety checks."""

    def testSettingsRejectInvalidValues(self) -> None:
        """Invalid TTLs, names and insecure prefixed cookies fail at boot."""
        for values in (
            {"lifetime": 0},
            {"lifetime": True},
            {"cookie": "bad;name"},
            {"cookie": "__Host-test", "secure": False},
        ):
            with self.assertRaises(ValueError):
                RememberAuth(**values)
        with self.assertRaises(TypeError):
            RememberAuth(secure="false")

    async def testControllerPassesExplicitOptInAndRetiresUsernameCookie(self) -> None:
        """The login checkbox requests authentication persistence, not autofill."""
        controller = LoginController(build_app())
        for value, expected in (("on", True), (None, False), ("false", False)):
            auth = SimpleNamespace(attempt=AsyncMock(return_value=True))
            payload = SimpleNamespace(email="ada@example.com", password="Secret1!")  # noqa: S106
            incoming = SimpleNamespace(data=AsyncMock(return_value={"remember": value}))
            outgoing = await controller.login(incoming, payload, auth)
            self.assertEqual(auth.attempt.call_args.kwargs, {"remember": expected})
            self.assertIn("usrname=", outgoing.getHeader("set-cookie")[0])
            self.assertIn("Max-Age=0", outgoing.getHeader("set-cookie")[0])
