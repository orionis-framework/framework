from unittest.mock import AsyncMock, MagicMock
from markupsafe import Markup, escape
from orionis.test import TestCase
from orionis.view import helpers
from orionis.view.helpers import (
    _global_app,
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

class TestGlobalConfig(TestCase):

    def testConfigCallableIsCallable(self) -> None:
        """
        Confirm the closure returned by _global_config is callable.

        Validates that the returned object can be invoked as a function
        inside a Jinja2 template context.
        """
        app = MagicMock()
        config = _global_config(app)
        self.assertTrue(callable(config))

    def testConfigReturnsAppConfigValue(self) -> None:
        """
        Retrieve a configuration value via the config callable.

        Validates that calling the returned closure delegates to
        app.config(key) and returns the resolved result.
        """
        app = MagicMock()
        app.config.return_value = "test-app"
        config = _global_config(app)
        result = config("app.name")
        self.assertEqual(result, "test-app")

    def testConfigReturnsDefaultWhenValueIsMissing(self) -> None:
        """
        Return the caller default when the key resolves to None.

        Validates that the closure falls back locally instead of
        propagating an absent configuration value.
        """
        app = MagicMock()
        app.config.return_value = None
        config = _global_config(app)
        result = config("missing.key", default="fallback")
        self.assertEqual(result, "fallback")
        app.config.assert_called_once_with("missing.key")

    def testConfigCallsAppConfigWithKey(self) -> None:
        """
        Forward the key argument to app.config unchanged.

        Validates that the closure calls app.config with exactly the key
        provided by the template, with no transformation.
        """
        app = MagicMock()
        app.config.return_value = "value"
        config = _global_config(app)
        config("database.host")
        app.config.assert_called_once_with("database.host")

class TestGlobalPythonVersion(TestCase):

    def testPythonVersionCallableIsCallable(self) -> None:
        """
        Confirm the closure returned by _global_python_version is callable.

        Validates that the returned object can be invoked as a function
        inside a Jinja2 template context.
        """
        version_fn = _global_python_version()
        self.assertTrue(callable(version_fn))

    def testPythonVersionReturnsSemverString(self) -> None:
        """
        Return the running Python version in X.X.X format.

        Validates that the closure reports the interpreter version as a
        dotted major.minor.micro string.
        """
        import sys

        version_fn = _global_python_version()
        expected = (
            f"{sys.version_info.major}."
            f"{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        )
        self.assertEqual(version_fn(), expected)

class TestGlobalFrameworkVersion(TestCase):

    def testFrameworkVersionCallableIsCallable(self) -> None:
        """
        Confirm the closure returned by _global_framework_version is callable.

        Validates that the returned object can be invoked as a function
        inside a Jinja2 template context.
        """
        version_fn = _global_framework_version()
        self.assertTrue(callable(version_fn))

    def testFrameworkVersionReturnsMetadataVersion(self) -> None:
        """
        Return the framework version declared in the metadata module.

        Validates that the closure resolves the VERSION constant so
        templates always report the installed framework release.
        """
        from orionis.metadata import VERSION

        version_fn = _global_framework_version()
        self.assertEqual(version_fn(), VERSION)

class TestGlobalApp(TestCase):

    def testAppCallableIsCallable(self) -> None:
        """
        Confirm the closure returned by _global_app is callable.

        Validates that the returned object can be invoked as a function
        inside a Jinja2 template context.
        """
        app = MagicMock()
        app_fn = _global_app(app)
        self.assertTrue(callable(app_fn))

    def testAppCallableReturnsApplicationInstance(self) -> None:
        """
        Return the application instance from the app closure.

        Validates that invoking the closure always returns the same
        application reference that was passed to _global_app.
        """
        app = MagicMock()
        app_fn = _global_app(app)
        result = app_fn()
        self.assertIs(result, app)

    def testAppCallableReturnsSameInstanceOnMultipleCalls(self) -> None:
        """
        Return the same application instance on repeated invocations.

        Validates that the closure is a stable reference and does not
        create or return a different object on each call.
        """
        app = MagicMock()
        app_fn = _global_app(app)
        self.assertIs(app_fn(), app_fn())

class TestGlobalRequest(TestCase):

    async def testRequestCallableIsCallable(self) -> None:
        """
        Confirm the closure returned by _global_request is callable.

        Validates that the returned async callable can be awaited in a
        Jinja2 async template environment.
        """
        app = MagicMock()
        request_fn = _global_request(app)
        self.assertTrue(callable(request_fn))

    async def testRequestReturnsNoneWhenMakeRaises(self) -> None:
        """
        Return None when app.make raises an exception.

        Validates that the request closure swallows all exceptions and
        returns None when the request service cannot be resolved.
        """
        app = MagicMock()
        app.make = AsyncMock(side_effect=RuntimeError("no request scope"))
        request_fn = _global_request(app)
        result = await request_fn()
        self.assertIsNone(result)

    async def testRequestReturnsResolvedRequest(self) -> None:
        """
        Return the resolved request object from the app container.

        Validates that the closure returns whatever app.make produces
        when a request is in scope and resolution succeeds.
        """
        fake_request = MagicMock()
        app = MagicMock()
        app.make = AsyncMock(return_value=fake_request)
        request_fn = _global_request(app)
        result = await request_fn()
        self.assertIs(result, fake_request)

class TestGlobalSession(TestCase):

    async def testSessionCallableIsCallable(self) -> None:
        """
        Confirm the closure returned by _global_session is callable.

        Validates that the returned async callable can be awaited in a
        Jinja2 async template environment.
        """
        app = MagicMock()
        session_fn = _global_session(app)
        self.assertTrue(callable(session_fn))

    async def testSessionReturnsNoneWhenMakeRaises(self) -> None:
        """
        Return None when app.make raises an exception.

        Validates that the session closure swallows all exceptions and
        returns None when the session service cannot be resolved.
        """
        app = MagicMock()
        app.make = AsyncMock(side_effect=RuntimeError("no session scope"))
        session_fn = _global_session(app)
        result = await session_fn()
        self.assertIsNone(result)

    async def testSessionReturnsResolvedSession(self) -> None:
        """
        Return the resolved session object from the app container.

        Validates that the closure returns whatever app.make produces
        when a session is in scope and resolution succeeds.
        """
        fake_session = MagicMock()
        app = MagicMock()
        app.make = AsyncMock(return_value=fake_session)
        session_fn = _global_session(app)
        result = await session_fn()
        self.assertIs(result, fake_session)

class TestGlobalDateTime(TestCase):

    def testNowReturnsDateTimeWithTimeComponent(self) -> None:
        """
        Return a date and time value from the now closure.

        Validates that the closure exposes the current instant with the
        attributes templates rely on for formatting.
        """
        now_fn = _global_now()
        value = now_fn()
        self.assertTrue(hasattr(value, "hour"))
        self.assertTrue(hasattr(value, "year"))

    def testTodayReturnsDateWithoutTimeComponent(self) -> None:
        """
        Return the current date from the today closure.

        Validates that the closure exposes the calendar day with its
        time truncated to midnight.
        """
        today_fn = _global_today()
        value = today_fn()
        self.assertTrue(hasattr(value, "year"))
        self.assertEqual(value.hour, 0)
        self.assertEqual(value.minute, 0)
        self.assertEqual(value.second, 0)

    def testTodayMatchesNowCalendarDate(self) -> None:
        """
        Report the same calendar date as the now closure.

        Validates that both closures resolve through the same
        configured timezone.
        """
        now_value = _global_now()()
        today_value = _global_today()()
        self.assertEqual(today_value.year, now_value.year)
        self.assertEqual(today_value.month, now_value.month)

class TestGlobalSecureUrl(TestCase):

    async def testSecureUrlUpgradesRequestScheme(self) -> None:
        """
        Rewrite the request base URL to the HTTPS scheme.

        Validates that a plain-HTTP base URL is upgraded before the
        path is appended.
        """
        request = MagicMock()
        request.baseUrl = "http://localhost:8000"
        app = MagicMock()
        app.make = AsyncMock(return_value=request)
        secure_url = _global_secure_url(app)
        result = await secure_url("/dashboard")
        self.assertEqual(result, "https://localhost:8000/dashboard")

    async def testSecureUrlKeepsRelativePathWithoutRequest(self) -> None:
        """
        Return the normalised path when no request is in scope.

        Validates that no host is invented when the base URL cannot be
        resolved from the container.
        """
        app = MagicMock()
        app.make = AsyncMock(side_effect=RuntimeError("no request scope"))
        secure_url = _global_secure_url(app)
        result = await secure_url("dashboard")
        self.assertEqual(result, "/dashboard")

    async def testSecureUrlAppendsQueryString(self) -> None:
        """
        Append keyword arguments as the query string.

        Validates that the query string is built before the scheme is
        forced to HTTPS.
        """
        app = MagicMock()
        app.make = AsyncMock(side_effect=RuntimeError("no request scope"))
        secure_url = _global_secure_url(app)
        result = await secure_url("//cdn.example.com/app", page=2)
        self.assertEqual(result, "https://cdn.example.com/app?page=2")

class TestGlobalSecureAsset(TestCase):

    async def testSecureAssetUpgradesDiskUrlScheme(self) -> None:
        """
        Rewrite the disk file URL to the HTTPS scheme.

        Validates that the URL produced by the storage disk is upgraded
        before it reaches the template.
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
        """
        Leave an already secure disk URL unchanged.

        Validates that no rewriting happens when the disk already
        returns an HTTPS URL.
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
        """
        Return safe markup so templates need no ``| safe`` filter.

        Validates that the hidden input is flagged as already-escaped
        HTML for the autoescaping environment.
        """
        app = self._appWithToken("abc123")
        field = await _global_csrf_field(app)()
        self.assertIsInstance(field, Markup)
        self.assertEqual(
            str(field),
            '<input type="hidden" name="_csrf" value="abc123">',
        )

    async def testCsrfFieldEscapesTokenValue(self) -> None:
        """
        Escape the token before embedding it in the hidden input.

        Validates that a hostile session value cannot break out of the
        attribute and inject markup.
        """
        token = '"><script>alert(1)</script>'  # noqa: S105
        app = self._appWithToken(token)
        field = await _global_csrf_field(app)()
        self.assertEqual(
            str(field),
            f'<input type="hidden" name="_csrf" value="{escape(token)}">',
        )
        self.assertNotIn("<script>", str(field))

class TestHelpersPackage(TestCase):

    def testEveryExportedBuilderIsCallable(self) -> None:
        """
        Verify every name exported by the helpers package is callable.

        Validates that the provider can invoke each builder to obtain
        the template global it registers.
        """
        for name in helpers.__all__:
            builder = getattr(helpers, name)
            self.assertTrue(callable(builder), msg=f"'{name}' is not callable")

    def testExportedNamesUseSnakeCasePrefix(self) -> None:
        """
        Verify every exported builder follows the naming convention.

        Validates that all helpers are exposed with the ``_global_``
        prefix expected by the view service provider.
        """
        for name in helpers.__all__:
            self.assertTrue(
                name.startswith("_global_"),
                msg=f"'{name}' does not follow the '_global_' convention",
            )
