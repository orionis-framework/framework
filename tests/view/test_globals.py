# ruff: noqa: PT009, S105
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Use an intentionally hostile synthetic CSRF token to verify HTML escaping.
"""Exercise built-in template helpers and request-scoped authentication."""

import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pendulum
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup, escape

from orionis.auth import Authenticatable
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.context.functions import bind_auth_context
from orionis.container.context.manager import ScopeManager
from orionis.metadata import VERSION
from orionis.support.facades import Auth
from orionis.support.facades.datetime import DateTime
from orionis.test import TestCase
from orionis.view import globals as view_globals
from orionis.view.extensions import CsrfExtension
from orionis.view.globals import (
    _global_app,
    _global_auth,
    _global_config,
    _global_csrf_field,
    _global_framework_version,
    _global_now,
    _global_python_version,
    _global_request,
    _global_secure_asset,
    _global_secure_url,
    _global_session,
    _global_today,
)

if TYPE_CHECKING:
    from jinja2 import Template

    from orionis.auth.contracts.authenticatable import IAuthenticatable


class TestGlobalConfig(TestCase):
    """Exercise global config behavior."""

    def testConfigCallableIsCallable(self) -> None:
        """Confirm the closure returned by _global_config is callable.

        Validates that the returned object can be invoked as a function
        inside a Jinja2 template context.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        config = _global_config(app)
        self.assertTrue(callable(config))

    def testConfigReturnsAppConfigValue(self) -> None:
        """Retrieve a configuration value via the config callable.

        Validates that calling the returned closure delegates to
        app.config(key) and returns the resolved result.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app.config.return_value = "test-app"
        config = _global_config(app)
        result = config("app.name")
        self.assertEqual(result, "test-app")

    def testConfigReturnsDefaultWhenValueIsMissing(self) -> None:
        """Return the caller default when the key resolves to None.

        Validates that the closure falls back locally instead of
        propagating an absent configuration value.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app.config.return_value = None
        config = _global_config(app)
        result = config("missing.key", default="fallback")
        self.assertEqual(result, "fallback")
        app.config.assert_called_once_with("missing.key")

    def testConfigCallsAppConfigWithKey(self) -> None:
        """Forward the key argument to app.config unchanged.

        Validates that the closure calls app.config with exactly the key
        provided by the template, with no transformation.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app.config.return_value = "value"
        config = _global_config(app)
        config("database.host")
        app.config.assert_called_once_with("database.host")


class TestGlobalPythonVersion(TestCase):
    """Exercise global python version behavior."""

    def testPythonVersionCallableIsCallable(self) -> None:
        """Confirm the closure returned by _global_python_version is callable.

        Validates that the returned object can be invoked as a function
        inside a Jinja2 template context.

        Returns
        -------
        None
            No return value.
        """
        version_fn = _global_python_version()
        self.assertTrue(callable(version_fn))

    def testPythonVersionReturnsSemverString(self) -> None:
        """Return the running Python version in X.X.X format.

        Validates that the closure reports the interpreter version as a
        dotted major.minor.micro string.

        Returns
        -------
        None
            No return value.
        """
        version_fn = _global_python_version()
        expected = (
            f"{sys.version_info.major}."
            f"{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        )
        self.assertEqual(version_fn(), expected)


class TestGlobalFrameworkVersion(TestCase):
    """Exercise global framework version behavior."""

    def testFrameworkVersionCallableIsCallable(self) -> None:
        """Confirm the closure returned by _global_framework_version is callable.

        Validates that the returned object can be invoked as a function
        inside a Jinja2 template context.

        Returns
        -------
        None
            No return value.
        """
        version_fn = _global_framework_version()
        self.assertTrue(callable(version_fn))

    def testFrameworkVersionReturnsMetadataVersion(self) -> None:
        """Return the framework version declared in the metadata module.

        Validates that the closure resolves the VERSION constant so
        templates always report the installed framework release.

        Returns
        -------
        None
            No return value.
        """
        version_fn = _global_framework_version()
        self.assertEqual(version_fn(), VERSION)


class TestGlobalApp(TestCase):
    """Exercise global app behavior."""

    def testAppCallableIsCallable(self) -> None:
        """Confirm the closure returned by _global_app is callable.

        Validates that the returned object can be invoked as a function
        inside a Jinja2 template context.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app_fn = _global_app(app)
        self.assertTrue(callable(app_fn))

    def testAppCallableReturnsApplicationInstance(self) -> None:
        """Return the application instance from the app closure.

        Validates that invoking the closure always returns the same
        application reference that was passed to _global_app.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app_fn = _global_app(app)
        result = app_fn()
        self.assertIs(result, app)

    def testAppCallableReturnsSameInstanceOnMultipleCalls(self) -> None:
        """Return the same application instance on repeated invocations.

        Validates that the closure is a stable reference and does not
        create or return a different object on each call.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app_fn = _global_app(app)
        self.assertIs(app_fn(), app_fn())


class TestGlobalRequest(TestCase):
    """Exercise global request behavior."""

    async def testRequestCallableIsCallable(self) -> None:
        """Confirm the closure returned by _global_request is callable.

        Validates that the returned async callable can be awaited in a
        Jinja2 async template environment.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        request_fn = _global_request(app)
        self.assertTrue(callable(request_fn))

    async def testRequestReturnsNoneWhenMakeRaises(self) -> None:
        """Return None when app.make raises an exception.

        Validate the optional fallback when the request service cannot
        be resolved; central failure observation is covered separately.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app.make = AsyncMock(side_effect=RuntimeError("no request scope"))
        request_fn = _global_request(app)
        result = await request_fn()
        self.assertIsNone(result)

    async def testRequestReturnsResolvedRequest(self) -> None:
        """Return the resolved request object from the app container.

        Validates that the closure returns whatever app.make produces
        when a request is in scope and resolution succeeds.

        Returns
        -------
        None
            No return value.
        """
        fake_request = MagicMock()
        app = MagicMock()
        app.make = AsyncMock(return_value=fake_request)
        request_fn = _global_request(app)
        result = await request_fn()
        self.assertIs(result, fake_request)


class TestGlobalSession(TestCase):
    """Exercise global session behavior."""

    async def testSessionCallableIsCallable(self) -> None:
        """Confirm the closure returned by _global_session is callable.

        Validates that the returned async callable can be awaited in a
        Jinja2 async template environment.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        session_fn = _global_session(app)
        self.assertTrue(callable(session_fn))

    async def testSessionReturnsNoneWhenMakeRaises(self) -> None:
        """Return None when app.make raises an exception.

        Validate the optional fallback when the session service cannot
        be resolved; central failure observation is covered separately.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app.make = AsyncMock(side_effect=RuntimeError("no session scope"))
        session_fn = _global_session(app)
        result = await session_fn()
        self.assertIsNone(result)

    async def testSessionReturnsResolvedSession(self) -> None:
        """Return the resolved session object from the app container.

        Validates that the closure returns whatever app.make produces
        when a session is in scope and resolution succeeds.

        Returns
        -------
        None
            No return value.
        """
        fake_session = MagicMock()
        app = MagicMock()
        app.make = AsyncMock(return_value=fake_session)
        session_fn = _global_session(app)
        result = await session_fn()
        self.assertIs(result, fake_session)


class TestGlobalDateTime(TestCase):
    """Exercise date helpers with one fixed instant in the configured timezone."""

    def setUp(self) -> None:
        """Fix both facade clocks without changing shared timezone configuration.

        Returns
        -------
        None
            No return value.
        """
        self._instant = pendulum.datetime(2031, 1, 15, 15, 47, tz="America/Bogota")
        self.enterContext(patch.object(DateTime, "now", return_value=self._instant))
        self.enterContext(
            patch.object(DateTime, "today", return_value=self._instant.start_of("day")),
        )

    def testNowReturnsDateTimeWithTimeComponent(self) -> None:
        """Return a date and time value from the now closure.

        Validates that the closure exposes the current instant with the
        attributes templates rely on for formatting.

        Returns
        -------
        None
            No return value.
        """
        now_fn = _global_now()
        value = now_fn()
        self.assertIs(value, self._instant)

    def testTodayReturnsMidnightInTheConfiguredTimezone(self) -> None:
        """Return midnight from the today closure in its configured timezone.

        Validates that the closure exposes the calendar day with its
        time truncated to midnight.

        Returns
        -------
        None
            No return value.
        """
        today_fn = _global_today()
        value = today_fn()
        self.assertIsInstance(value, pendulum.DateTime)
        self.assertEqual(value.timezone_name, "America/Bogota")
        self.assertEqual(value.hour, 0)
        self.assertEqual(value.minute, 0)
        self.assertEqual(value.second, 0)

    def testTodayMatchesNowCalendarDate(self) -> None:
        """Report the same calendar date as the now closure.

        Validates that both closures resolve through the same
        configured timezone.

        Returns
        -------
        None
            No return value.
        """
        now_value = _global_now()()
        today_value = _global_today()()
        self.assertEqual(today_value.year, now_value.year)
        self.assertEqual(today_value.month, now_value.month)
        self.assertEqual(today_value.day, now_value.day)
        self.assertEqual(today_value.timezone_name, now_value.timezone_name)


class TestGlobalSecureUrl(TestCase):
    """Exercise global secure url behavior."""

    async def testSecureUrlUpgradesRequestScheme(self) -> None:
        """Rewrite the request base URL to the HTTPS scheme.

        Validates that a plain-HTTP base URL is upgraded before the
        path is appended.

        Returns
        -------
        None
            No return value.
        """
        request = MagicMock()
        request.baseUrl = "http://localhost:8000"
        app = MagicMock()
        app.make = AsyncMock(return_value=request)
        secure_url = _global_secure_url(app)
        result = await secure_url("/dashboard")
        self.assertEqual(result, "https://localhost:8000/dashboard")

    async def testSecureUrlKeepsRelativePathWithoutRequest(self) -> None:
        """Return the normalised path when no request is in scope.

        Validates that no host is invented when the base URL cannot be
        resolved from the container.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app.make = AsyncMock(side_effect=RuntimeError("no request scope"))
        secure_url = _global_secure_url(app)
        result = await secure_url("dashboard")
        self.assertEqual(result, "/dashboard")

    async def testSecureUrlAppendsQueryString(self) -> None:
        """Append keyword arguments as the query string.

        Validates that the query string is built before the scheme is
        forced to HTTPS.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app.make = AsyncMock(side_effect=RuntimeError("no request scope"))
        secure_url = _global_secure_url(app)
        result = await secure_url("//cdn.example.com/app", page=2)
        self.assertEqual(result, "https://cdn.example.com/app?page=2")


class TestGlobalSecureAsset(TestCase):
    """Exercise global secure asset behavior."""

    async def testSecureAssetUpgradesDiskUrlScheme(self) -> None:
        """Rewrite the disk file URL to the HTTPS scheme.

        Validates that the URL produced by the storage disk is upgraded
        before it reaches the template.

        Returns
        -------
        None
            No return value.
        """
        file_mock = MagicMock()
        file_mock.url = AsyncMock(return_value="http://cdn.example.com/a.css")
        disk_mock = MagicMock()
        disk_mock.file.return_value = file_mock
        storage = MagicMock()
        storage.disk.return_value = disk_mock
        app = MagicMock()
        app.make = AsyncMock(return_value=storage)

        secure_asset = _global_secure_asset(app)
        result = await secure_asset("a.css")
        self.assertEqual(result, "https://cdn.example.com/a.css")

    async def testSecureAssetKeepsHttpsUrlUntouched(self) -> None:
        """Leave an already secure disk URL unchanged.

        Validates that no rewriting happens when the disk already
        returns an HTTPS URL.

        Returns
        -------
        None
            No return value.
        """
        file_mock = MagicMock()
        file_mock.url = AsyncMock(return_value="https://cdn.example.com/a.css")
        disk_mock = MagicMock()
        disk_mock.file.return_value = file_mock
        storage = MagicMock()
        storage.disk.return_value = disk_mock
        app = MagicMock()
        app.make = AsyncMock(return_value=storage)

        secure_asset = _global_secure_asset(app)
        result = await secure_asset("a.css", disk="s3")
        self.assertEqual(result, "https://cdn.example.com/a.css")
        storage.disk.assert_called_once_with("s3")


class TestGlobalCsrfField(TestCase):
    """Exercise global csrf field behavior."""

    @staticmethod
    def _appWithToken(token: str) -> MagicMock:
        """
        Build an application mock whose session holds a CSRF token.

        Parameters
        ----------
        token : str
            Token value returned by the mocked session.

        Returns
        -------
        MagicMock
            Application mock wired to resolve the mocked session.
        """
        session = MagicMock()
        session.get.return_value = token
        app = MagicMock()
        app.make = AsyncMock(return_value=session)
        app.config.return_value = None
        return app

    async def testCsrfFieldReturnsMarkup(self) -> None:
        """Return safe markup so templates need no ``| safe`` filter.

        Validates that the hidden input is flagged as already-escaped
        HTML for the autoescaping environment.

        Returns
        -------
        None
            No return value.
        """
        app = self._appWithToken("abc123")
        field = await _global_csrf_field(app)()
        self.assertIsInstance(field, Markup)
        self.assertEqual(
            str(field),
            '<input type="hidden" name="_csrf" value="abc123">',
        )

    async def testCsrfFieldEscapesTokenValue(self) -> None:
        """Escape the token before embedding it in the hidden input.

        Validates that a hostile session value cannot break out of the
        attribute and inject markup.

        Returns
        -------
        None
            No return value.
        """
        token = '"><script>alert(1)</script>'
        app = self._appWithToken(token)
        field = await _global_csrf_field(app)()
        self.assertEqual(
            str(field),
            f'<input type="hidden" name="_csrf" value="{escape(token)}">',
        )
        self.assertNotIn("<script>", str(field))


class _AuthIdentity(Authenticatable):
    """Represent an identity scoped to a template render."""

    __slots__ = ("email", "name")

    def __init__(self, name: str, email: str) -> None:
        """Initialize an authenticatable identity for template rendering.

        Parameters
        ----------
        name : str
            Display name exposed to the template.
        email : str
            Email address exposed to the template.

        Returns
        -------
        None
            No return value.
        """
        self.name = name
        self.email = email


class TestGlobalAuth(TestCase):
    """Exercise global auth behavior."""

    def setUp(self) -> None:
        """Register the authentication global before entering a request scope.

        Returns
        -------
        None
            No return value.
        """
        self._environment = Environment(enable_async=True, autoescape=True)
        self._environment.globals["auth"] = _global_auth()
        self._template_path = (
            Path(__file__).resolve().parents[2] / "resources" / "views"
        )

    @staticmethod
    async def _renderForIdentity(
        template: Template,
        identity: _AuthIdentity | None,
        barrier: asyncio.Barrier | None = None,
    ) -> str:
        """
        Render a template inside an independent authentication scope.

        Parameters
        ----------
        template : Template
            Shared template rendered without controller-supplied context.
        identity : _AuthIdentity | None
            User bound to the scope, or ``None`` for a guest.
        barrier : asyncio.Barrier | None, optional
            Gate ensuring all concurrent identities are bound before rendering.

        Returns
        -------
        str
            Rendered template using only the current scope's identity.
        """
        async with ScopeManager():
            bind_auth_context(
                AuthenticationContext(
                    identity=cast("IAuthenticatable | None", identity),
                    guard="session",
                ),
            )
            if barrier is not None:
                await barrier.wait()
            return await template.render_async()

    def testReturnsAuthenticationFacade(self) -> None:
        """Expose the public authentication facade from the template global.

        Returns
        -------
        None
            No return value.
        """
        auth = _global_auth()
        self.assertIs(auth(), Auth)
        self.assertIs(auth(), Auth)

    async def testRendersUserWithoutControllerContext(self) -> None:
        """Render authenticated user attributes through the facade global.

        Returns
        -------
        None
            No return value.
        """
        template = self._environment.from_string(
            "{{ auth().user().name }}|{{ auth().user().email }}|"
            "{{ auth().check() }}|{{ auth().guest() }}",
        )
        identity = _AuthIdentity("Alice <Admin>", "alice@example.test")
        rendered = await self._renderForIdentity(template, identity)
        self.assertEqual(
            rendered,
            "Alice &lt;Admin&gt;|alice@example.test|True|False",
        )

    async def testRendersGuestWithoutAUser(self) -> None:
        """Render guest state without requiring an authenticated identity.

        Returns
        -------
        None
            No return value.
        """
        template = self._environment.from_string(
            "{{ auth().user() is none }}|{{ auth().check() }}|{{ auth().guest() }}",
        )
        rendered = await self._renderForIdentity(template, None)
        self.assertEqual(rendered, "True|False|True")

    async def testRendersIsolatedUsersAcrossScopes(self) -> None:
        """Keep concurrent template renders isolated by authentication scope.

        Returns
        -------
        None
            No return value.
        """
        template = self._environment.from_string(
            "{{ auth().user().name }}|{{ auth().user().email }}",
        )
        identities = [
            _AuthIdentity(f"User {index}", f"user{index}@example.test")
            for index in range(8)
        ]
        barrier = asyncio.Barrier(len(identities))
        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(self._renderForIdentity(template, identity, barrier))
                for identity in identities
            ]
        rendered = [task.result() for task in tasks]
        self.assertEqual(
            rendered,
            [f"{identity.name}|{identity.email}" for identity in identities],
        )

    async def testRendersAuthenticatedLayoutsWithoutControllerContext(self) -> None:
        """Render the application pages using authentication from their layout.

        Returns
        -------
        None
            No return value.
        """
        environment = Environment(
            loader=FileSystemLoader(str(self._template_path)),
            extensions=[CsrfExtension],
            enable_async=True,
            autoescape=True,
            undefined=StrictUndefined,
        )
        environment.globals.update(
            {
                "auth": _global_auth(),
                "__": str,
                "config": {"app.locale": "en", "app.name": "Orionis"}.get,
                "framework_version": _global_framework_version(),
                "asset": lambda path: f"/assets/{path}",
                "route": lambda name: f"/{name}",
                "csrf_token": lambda: "test-csrf-value",
                "csrf_field": Markup,
            },
        )
        identity = _AuthIdentity("Template User", "template@example.test")
        pages = [
            await self._renderForIdentity(environment.get_template(path), identity)
            for path in (
                "home/index.html",
                "admin/roles/index.html",
                "admin/users/index.html",
            )
        ]
        for page in pages:
            self.assertIn(
                "<strong>Template User</strong><span>template@example.test</span>",
                page,
            )
        self.assertIn("Welcome back, Template User.", pages[0])


class TestHelpersPackage(TestCase):
    """Exercise helpers package behavior."""

    def testEveryExportedBuilderIsCallable(self) -> None:
        """Verify every name exported by the helpers package is callable.

        Validates that the provider can invoke each builder to obtain
        the template global it registers.

        Returns
        -------
        None
            No return value.
        """
        for name in view_globals.__all__:
            builder = getattr(view_globals, name)
            self.assertTrue(callable(builder), msg=f"'{name}' is not callable")

    def testExportedNamesUseSnakeCasePrefix(self) -> None:
        """Verify every exported builder follows the naming convention.

        Validates that all helpers are exposed with the ``_global_``
        prefix expected by the view service provider.

        Returns
        -------
        None
            No return value.
        """
        for name in view_globals.__all__:
            self.assertTrue(
                name.startswith("_global_"),
                msg=f"'{name}' does not follow the '_global_' convention",
            )
