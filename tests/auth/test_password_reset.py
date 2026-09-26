import asyncio
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
from database.migrations import (
    m0000000012_create_password_reset_tokens_table as reset_migration,
)
from orionis.auth.guards.session_guard import SessionGuard
from orionis.auth.identity.provider import ModelIdentityProvider
from orionis.auth.middleware import AuthenticateSessionMiddleware, GuestMiddleware
from orionis.auth.passwords.broker import PasswordBroker
from orionis.auth.tokens.functions import hash_token_secret
from orionis.database.connection_manager import ConnectionManager
from orionis.database.schema.schema import Schema as DatabaseSchema
from orionis.foundation.config.auth import Auth, PasswordReset
from orionis.hashing.hash_manager import HashManager
from orionis.http.default.controllers.forgot_password_controller import (
    ForgotPasswordController,
)
from orionis.http.default.schemas.forgot_password import ForgotPasswordSchema
from orionis.http.default.schemas.reset_password import ResetPasswordSchema
from orionis.http.responses import HTMLResponse
from orionis.http.layer.web.exceptions import CSRFTokenMismatchException
from orionis.http.routes.route_resolver import RouteResolver
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.validator import Schema as Validator
from orionis.session.session import Session
from orionis.test import TestCase
from orionis.view.extensions.csrf import CsrfExtension
from tests.auth.test_identity_and_session import (
    Account,
    accounts_table,
    build_app,
    fake_request,
)
from tests.auth.test_tokens import tokens_table
from tests.http.routes.test_nested_routing import compile_router, make_router
from tests.http.test_kernel import (
    _IdentityMiddlewareDouble,
    _StubApp,
    boot_kernel,
    dispatch,
)

if TYPE_CHECKING:
    from collections.abc import Generator


class TestPasswordReset(TestCase):
    """Exercise persistence, races, hashing and revocation through the broker."""

    async def asyncSetUp(self) -> None:
        """Create independent disk-backed storage and a real password hasher."""
        self.temp = tempfile.TemporaryDirectory()
        self.app = build_app()
        self.app._config["database"]["connections"]["sqlite"]["database"] = str(
            Path(self.temp.name) / "reset.sqlite",
        )
        self.manager = ConnectionManager(self.app)
        self.previous = ConnectionResolver._manager
        ConnectionResolver.setManager(self.manager)
        self.connection = self.manager.connection("sqlite")
        for table in (accounts_table(), tokens_table()):
            await self.connection.createTable(table)
        with patch.object(reset_migration, "Schema", DatabaseSchema(self.manager)):
            await reset_migration.CreatePasswordResetTokensTable().up()
        self.hashing = HashManager(self.app)
        self.db = QueryBuilder(self.manager)
        self.broker = PasswordBroker(self.app, self.db, self.hashing)
        self.user = await Account.create(
            {
                "email": "ada@example.com",
                "active": True,
                "password": await self.hashing.make("OriginalPassword1!"),
            },
        )

    async def asyncTearDown(self) -> None:
        """Disconnect and remove only this test's temporary database."""
        ConnectionResolver.setManager(self.previous)
        await self.connection.disconnect()
        self.temp.cleanup()

    async def testStoresOnlyDigestAndDoesNotChangePassword(self) -> None:
        """Issuance must not change the account or store a bearer credential."""
        _, token = await self.broker.issue(" ADA@example.com ")
        row = await self.db.table("password_reset_tokens").first()
        self.assertEqual(row["token"], hash_token_secret(token))
        self.assertNotIn(token, repr(row))
        self.assertEqual(len(token), 43)
        self.assertEqual(
            (await Account.find(self.user.id)).password,
            self.user.password,
        )
        self.assertTrue(await self.broker.valid(self.user.email, token))
        self.assertTrue(await self.broker.valid(self.user.email, token))

    async def testUnknownEmailDoesNotCreateAToken(self) -> None:
        """Unknown addresses do not grow the reset store."""
        self.assertIsNone(await self.broker.issue("missing@example.com"))
        self.assertEqual(await self.db.table("password_reset_tokens").count(), 0)

    async def testCooldownAndReplacementInvalidatePreviousLink(self) -> None:
        """Resends are throttled and only the newest link remains usable."""
        _, token = await self.broker.issue(self.user.email)
        self.assertIsNone(await self.broker.issue(self.user.email))
        await self.db.table("password_reset_tokens").update(
            {
                "created_at": int(time.time()) - 60,
            },
        )
        _, replacement = await self.broker.issue(self.user.email)
        self.assertFalse(await self.broker.valid(self.user.email, token))
        self.assertTrue(await self.broker.valid(self.user.email, replacement))

    async def testConcurrentIssueCreatesExactlyOneCredential(self) -> None:
        """The primary key arbitrates first requests across separate tasks."""
        results = await asyncio.gather(
            *(self.broker.issue(self.user.email) for _ in range(6)),
        )
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(await self.db.table("password_reset_tokens").count(), 1)

    async def testExpiredTamperedAndWrongAccountLinksAreRejected(self) -> None:
        """A token is bound to its recipient and expires at the boundary."""
        _, token = await self.broker.issue(self.user.email)
        self.assertFalse(await self.broker.valid("other@example.com", token))
        self.assertFalse(await self.broker.valid(self.user.email, "!" * 43))
        self.assertFalse(await self.broker.valid(self.user.email, "x" * 43))
        await self.db.table("password_reset_tokens").update(
            {
                "created_at": int(time.time()) - 3600,
            },
        )
        self.assertIsNone(
            await self.broker.reset(self.user.email, token, "NewPassword1!"),
        )
        self.assertEqual(
            (await Account.find(self.user.id)).password,
            self.user.password,
        )

    async def testResetHashesPasswordRevokesTokensAndSessions(self) -> None:
        """A successful reset requires fresh login and invalidates old access."""
        guard = SessionGuard(self.app, ModelIdentityProvider(self.app, self.hashing))
        request = fake_request(Session())
        guard.login(request, self.user)
        api_token = await self.broker.tokens.create(self.user, "test")
        _, token = await self.broker.issue(self.user.email)
        result = await self.broker.reset(self.user.email, token, "NewPassword1!")
        self.assertIsNotNone(result)
        updated = await Account.find(self.user.id)
        self.assertTrue(await self.hashing.check("NewPassword1!", updated.password))
        self.assertFalse(
            await self.hashing.check("OriginalPassword1!", updated.password),
        )
        self.assertIsNone(await guard.resolve(request))
        self.assertIsNone(
            await self.broker.tokens.findByPlainText(api_token.plain_text),
        )
        self.assertIsNone(
            await self.broker.reset(self.user.email, token, "Different1!"),
        )
        self.assertIsNone(await self.broker.issue(self.user.email))

    async def testConcurrentConsumptionHasOneWinner(self) -> None:
        """One credential can commit exactly one update across concurrent tasks."""
        _, token = await self.broker.issue(self.user.email)
        results = await asyncio.gather(
            *(
                self.broker.reset(self.user.email, token, f"Password{i}!")
                for i in range(4)
            ),
        )
        self.assertEqual(sum(result is not None for result in results), 1)

    async def testTransactionFailureRestoresPasswordAndToken(self) -> None:
        """A failure after the password write must roll back both mutations."""
        _, token = await self.broker.issue(self.user.email)
        with (
            patch.object(
                type(self.broker.tokens),
                "revokeAll",
                new=AsyncMock(side_effect=RuntimeError),
            ),
            self.assertRaises(RuntimeError),
        ):
            await self.broker.reset(self.user.email, token, "NewPassword1!")
        self.assertTrue(await self.broker.valid(self.user.email, token))
        self.assertEqual(
            (await Account.find(self.user.id)).password,
            self.user.password,
        )

    async def testIndependentPasswordChangeInvalidatesTheLink(self) -> None:
        """A link must not survive a password change through another flow."""
        _, token = await self.broker.issue(self.user.email)
        await (
            Account.query()
            .where("id", self.user.id)
            .update(
                {
                    "password": await self.hashing.make("ChangedPassword1!"),
                },
            )
        )
        self.assertFalse(await self.broker.valid(self.user.email, token))

    async def testDeletedAccountCannotTransferLinkToReplacement(self) -> None:
        """Reusing an email address must not transfer a previous reset grant."""
        _, token = await self.broker.issue(self.user.email)
        await Account.query().where("id", self.user.id).delete()
        await Account.create(
            {
                "id": 99,
                "email": self.user.email,
                "password": self.user.password,
            },
        )
        self.assertFalse(await self.broker.valid(self.user.email, token))

    async def testLegacySessionWithoutPasswordFingerprintIsRejected(self) -> None:
        """Pre-upgrade sessions must log in again rather than evade revocation."""
        session = Session()
        session.put("_auth_identifier", self.user.id)
        guard = SessionGuard(self.app, ModelIdentityProvider(self.app, self.hashing))
        self.assertIsNone(await guard.resolve(fake_request(session)))
        self.assertIsNone(session.get("_auth_identifier"))


class TestPasswordResetValidation(TestCase):
    """Enforce credential policy and trusted link configuration."""

    def testRejectsWeakMismatchedAndOversizedPasswords(self) -> None:
        """Schema validation includes inherited email rules and confirmation."""
        valid = {
            "email": "ada@example.com",
            "token": "x" * 43,
            "password": "NewPassword1!",
            "password_confirmation": "NewPassword1!",
        }
        Validator.validate(valid, ResetPasswordSchema)
        for changes in (
            {"password": "weak"},
            {"password_confirmation": "Mismatch1!"},
            {"password": "a" * 1025},
            {"email": "invalid"},
            {"token": "short"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValidationException):
                Validator.validate({**valid, **changes}, ResetPasswordSchema)

    def testPasswordResetLimitsMustBePositive(self) -> None:
        """Reset lifetime and cooldown must be positive integers."""
        self.assertIsInstance(
            Auth(passwords={"expiration": 15}).passwords,
            PasswordReset,
        )
        for values in ({"expiration": 0}, {"throttle": -1}, {"expiration": True}):
            with self.assertRaises(ValueError):
                PasswordReset(**values)


class _View:
    """Record explicit context and errors without a live view container."""

    def __init__(self, context: dict) -> None:
        """Capture template context."""
        self.context = context
        self.errors = None

    def withErrors(self, errors):
        """Capture field errors without persisting any submitted input."""
        self.errors = errors
        return self

    def __await__(self) -> Generator[object, None, HTMLResponse]:
        """Return an ordinary response from the awaitable view double."""

        async def render():
            return HTMLResponse("form")

        return render().__await__()


class TestPasswordResetController(TestCase):
    """Test browser responses and mail construction without sending email."""

    async def testMailUsesRequestBaseUrlAndEncodedRecipient(self) -> None:
        """Mail uses the request origin and encodes the recipient."""
        controller = ForgotPasswordController()
        email = "ada+test@example.com"
        broker = SimpleNamespace(
            issue=AsyncMock(return_value=(SimpleNamespace(email=email), "x" * 43)),
            settings=PasswordReset(),
        )
        module = "orionis.http.default.controllers.forgot_password_controller"
        with patch(module + ".Mail") as mail, patch(module + ".Lang") as lang:
            lang.get.side_effect = lambda message: message
            pending = mail.to.return_value.subject.return_value
            pending.send = AsyncMock()
            await controller._sendLink(
                email,
                "http://192.168.1.20:8000/base",
                broker,
            )
        mail.to.assert_called_once_with(email)
        content = pending.send.call_args.args[0]
        parsed = urlsplit(content.data["reset_url"])
        self.assertEqual(parsed.netloc, "192.168.1.20:8000")
        self.assertEqual(parsed.path, "/base/reset-password")
        self.assertEqual(parse_qs(parsed.query)["email"], [email])
        self.assertEqual(content.data["expires_minutes"], 60)

    async def testMailFailureLogsNoCredential(self) -> None:
        """Background failures never escape or disclose exception parameters."""
        broker = SimpleNamespace(
            issue=AsyncMock(
                side_effect=RuntimeError("secret-bearing-backend-error"),
            ),
        )
        with self.assertLogs(level="ERROR") as logs:
            await ForgotPasswordController()._sendLink(
                "ada@example.com",
                "http://192.168.1.20:8000",
                broker,
            )
        self.assertNotIn("secret-bearing-backend-error", str(logs.output))

    async def testSuccessRedirectsToLoginAndQueuesNotification(self) -> None:
        """Successful reset does not establish an authenticated session."""
        controller = ForgotPasswordController()
        broker = SimpleNamespace(
            valid=AsyncMock(return_value=True),
            reset=AsyncMock(return_value=SimpleNamespace(email="ada@example.com")),
        )
        request = SimpleNamespace(
            data=AsyncMock(
                return_value={
                    "email": "ada@example.com",
                    "token": "x" * 43,
                    "password": "NewPassword1!",
                    "password_confirmation": "NewPassword1!",
                },
            ),
        )
        module = "orionis.http.default.controllers.forgot_password_controller"
        with patch(module + ".Lang") as lang:
            lang.get.side_effect = lambda message: message
            result = await controller.resetPassword(request, broker)
        self.assertEqual(result.getHeader("location"), ["/login"])
        self.assertIsNotNone(result.background)
        self.assertNotIn("token", str(result.getFlashData()))

    async def testReceiptIsIdenticalAndLookupRunsAfterResponse(self) -> None:
        """Known and unknown emails follow the same immediate response path."""
        controller = ForgotPasswordController()
        broker = SimpleNamespace(issue=AsyncMock(return_value=None))
        request = SimpleNamespace(baseUrl="http://192.168.1.20:8000")
        with patch(
            "orionis.http.default.controllers.forgot_password_controller.Lang",
        ) as lang:
            lang.get.side_effect = lambda message: message
            receipts = [
                await controller.sendResetLinkEmail(
                    ForgotPasswordSchema(email=email),
                    request,
                    broker,
                )
                for email in ("ada@example.com", "missing@example.com")
            ]
        broker.issue.assert_not_awaited()
        self.assertEqual(receipts[0].getFlashData(), receipts[1].getFlashData())
        self.assertEqual(receipts[0].getHeader("location"), ["/forgot-password"])
        self.assertEqual(receipts[0].getHeader("cache-control"), ["no-store"])
        await receipts[0].background()
        broker.issue.assert_awaited_once()

    async def testInvalidLinkRendersWithoutEchoingSecrets(self) -> None:
        """An invalid link gets a safe form state and private response headers."""
        controller = ForgotPasswordController()
        broker = SimpleNamespace(valid=AsyncMock(return_value=False))
        view = _View({})
        with patch(
            "orionis.http.factory.ResponseFactory.view",
            return_value=view,
        ) as render:
            result = await controller.showResetForm(
                SimpleNamespace(
                    queryParams={"email": "ada@example.com", "token": "x" * 43},
                ),
                broker,
            )
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.getHeader("referrer-policy"), ["no-referrer"])
        self.assertEqual(
            render.call_args.kwargs,
            {"valid": False, "email": "", "token": ""},
        )

    async def testValidationFailureNeverConsumesOrFlashesPassword(self) -> None:
        """Passwords stay out of context and flash data when confirmation fails."""
        controller = ForgotPasswordController()
        broker = SimpleNamespace(valid=AsyncMock(return_value=True), reset=AsyncMock())
        data = {
            "email": "ada@example.com",
            "token": "x" * 43,
            "password": "NewPassword1!",
            "password_confirmation": "Wrong1!",
        }
        view = _View({})
        with patch(
            "orionis.http.factory.ResponseFactory.view",
            return_value=view,
        ) as render:
            result = await controller.resetPassword(
                SimpleNamespace(data=AsyncMock(return_value=data)),
                broker,
            )
        broker.reset.assert_not_awaited()
        self.assertIsNone(result.getFlashData())
        self.assertNotIn("password", render.call_args.kwargs)
        self.assertIsInstance(view.errors, ValidationException)


class TestPasswordResetWeb(TestCase):
    """Compile production routes, reject missing CSRF and render real views."""

    async def testRoutesAreWebAndPostRequiresCsrf(self) -> None:
        """Reset endpoints inherit the web pipeline's CSRF protection."""
        router = make_router()
        router.auth()
        compiled = compile_router(router)
        resolver = RouteResolver(compiled)
        for method, path, name in (
            ("POST", "/forgot-password", "forgot-password"),
            ("GET", "/reset-password", "password.reset"),
            ("POST", "/reset-password", "password.update"),
        ):
            route = resolver.resolve(method, path).route
            self.assertEqual(route.kind, "web")
            self.assertEqual(route.name, name)
        original_build = _StubApp.build

        async def build(app, concrete):
            if concrete in (GuestMiddleware, AuthenticateSessionMiddleware):
                return _IdentityMiddlewareDouble()
            return await original_build(app, concrete)

        with patch.object(_StubApp, "build", build):
            kernel, _app, _responses, catch = await boot_kernel(
                routes=compiled,
                csrf_enabled=True,
            )
        for path in ("/forgot-password", "/reset-password"):
            await dispatch(kernel, path, "POST")
            self.assertIsInstance(catch.handled[-1], CSRFTokenMismatchException)

    async def testTemplatesRenderWithEscapingAndCsrf(self) -> None:
        """Real forms escape attributes, include CSRF and leave passwords empty."""
        environment = Environment(
            loader=FileSystemLoader("resources/views"),
            extensions=[CsrfExtension],
            autoescape=True,
            enable_async=True,
        )
        environment.globals.update(
            {
                "__": lambda message, **_: message,
                "config": lambda _: "Orionis",
                "url": lambda path: path,
                "asset": lambda path: "/" + path,
                "route": lambda _: "/reset-password",
                "old": lambda _: "",
                "flash": lambda _: None,
                "csrf_token": lambda: "csrf-test",
                "csrf_field": lambda: Markup('<input name="_csrf" value="csrf-test">'),
                "errors": SimpleNamespace(any=lambda: False, has=lambda _: False),
            },
        )
        template = environment.get_template("auth/reset-password.html")
        html = await template.render_async(
            valid=True,
            email='ada"@example.com',
            token="x" * 43,
        )
        self.assertIn('name="_csrf"', html)
        self.assertIn("ada&#34;@example.com", html)
        self.assertIn('autocomplete="new-password"', html)
        invalid = await template.render_async(valid=False, email="", token="")
        self.assertNotIn('name="token"', invalid)
        await environment.get_template("auth/forgot-password.html").render_async()
        mail = await environment.get_template(
            "emails/reset-password.html",
        ).render_async(
            user_name="Ada",
            reset_url="https://trusted.example.com/?token=x",
            expires_minutes=60,
        )
        self.assertIn("https://trusted.example.com/?token=x", mail)
