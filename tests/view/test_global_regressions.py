# ruff: noqa: PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect URL composition, optional error bags, and global runtime annotations."""

import gc
import weakref
from inspect import getmodule, isfunction, unwrap
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import AsyncMock, MagicMock

import pendulum

from orionis.session.session import Session
from orionis.test import TestCase
from orionis.view import globals as view_globals
from orionis.view.globals.asset import _global_secure_asset
from orionis.view.globals.errors import ErrorBag
from orionis.view.globals.route import _build_route_path, _compile_route_template
from orionis.view.globals.url import _global_secure_url, _global_url, _to_secure_url


class _WeakTemplate(str):
    """Expose cache ownership through weak references to real string keys."""

    __slots__ = ("__weakref__",)
    """Allow weak references without adding a mutable instance dictionary."""


class TestViewGlobalRegressions(TestCase):
    """Exercise helper contracts without external services or a shared session."""

    async def testUrlQueryPrecedesTheFragment(self) -> None:
        """Append encoded arguments before every preserved URL fragment.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app.make = AsyncMock(
            return_value=SimpleNamespace(baseUrl="https://app.example.test"),
        )
        url = _global_url(app)
        for path, expected in (
            ("/page#section", "https://app.example.test/page?term=a+b#section"),
            (
                "/page?existing=yes#section",
                "https://app.example.test/page?existing=yes&term=a+b#section",
            ),
            (
                "https://other.example.test/page#fragment?raw=yes",
                "https://other.example.test/page?term=a+b#fragment?raw=yes",
            ),
            ("//cdn.example.test/file#v1", "//cdn.example.test/file?term=a+b#v1"),
        ):
            with self.subTest(path=path):
                self.assertEqual(await url(path, term="a b"), expected)

    async def testUnavailableErrorBagCannotPolluteAnotherRead(self) -> None:
        """Isolate missing-session results and preserve live-session borrowing.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app.make = AsyncMock(side_effect=RuntimeError("No active session"))
        first = ErrorBag(app)
        exposed = await first.all()
        self.addCleanup(exposed.clear)
        exposed["foreign"] = ["another request"]
        self.assertEqual(await ErrorBag(app).all(), {})
        self.assertFalse(await first.any())
        self.assertEqual(await first.get("foreign"), [])

        session = Session()
        session.flashErrors({"email": "Invalid"})
        app.make = AsyncMock(return_value=session)
        self.assertIs(await ErrorBag(app).all(), session.getErrors())

    def testGlobalBuildersAndCallbacksHaveResolvableAnnotations(self) -> None:
        """Resolve declared helpers and nested callbacks without injected namespaces.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app.config.return_value = None
        seen = set()
        for name in view_globals.__all__:
            builder = getattr(view_globals, name)
            module = getmodule(builder)
            functions = [
                unwrap(item)
                for item in vars(module).values()
                if getattr(item, "__module__", None) == module.__name__
                and isfunction(unwrap(item))
            ]
            callback = builder(app) if builder.__code__.co_argcount else builder()
            if isfunction(callback):
                functions.append(callback)
            elif isinstance(callback, ErrorBag):
                functions.extend(
                    item for item in vars(ErrorBag).values() if isfunction(item)
                )
            for function in functions:
                if function in seen or function.__name__ == "__annotate_func__":
                    continue
                seen.add(function)
                with self.subTest(method=function.__qualname__):
                    self.assertTrue(get_type_hints(function))
        self.assertIs(
            get_type_hints(view_globals._global_today())["return"],
            pendulum.DateTime,
        )

    async def testErrorBagAnyRequiresAtLeastOneMessage(self) -> None:
        """Ignore empty message lists when checking whether validation failed.

        Returns
        -------
        None
            No return value.
        """
        session = Session()
        session.flashErrors({"email": [], "name": []})
        app = MagicMock()
        app.make = AsyncMock(return_value=session)
        errors = ErrorBag(app)
        self.assertFalse(await errors.any())
        self.assertFalse(await errors.has("email"))
        self.assertEqual(await errors.first(), "")
        session.flashErrors({"name": ["Required"]})
        self.assertTrue(await errors.any())
        self.assertEqual(await errors.first(), "Required")

    def testRoutePlansBoundRetainedKeysAndRebuildEvictedEntries(self) -> None:
        """Bound retained templates while preserving interpolation after eviction.

        Returns
        -------
        None
            No return value.
        """
        clear = getattr(_compile_route_template, "cache_clear", None)
        if clear is not None:
            clear()
            self.addCleanup(clear)
        references = []
        refresh_index = 512
        params = {"id": "a/b", "page": 2}
        for index in range(1100):
            template = _WeakTemplate(f"/nodes/{index}/{{id:int}}/copy/{{id}}")
            references.append(weakref.ref(template))
            path, extra = _build_route_path(template, params)
            self.assertEqual(path, f"/nodes/{index}/a%2Fb/copy/a%2Fb")
            self.assertEqual(extra, {"page": 2})
            if index == refresh_index:
                _build_route_path(references[0](), params)
        del template
        gc.collect()
        retained = sum(reference() is not None for reference in references)
        self.assertLessEqual(retained, 1024)
        self.assertIsNotNone(references[0]())
        self.assertIsNone(references[1]())
        self.assertEqual(
            _build_route_path("/nodes/1/{id:int}/copy/{id}", params),
            ("/nodes/1/a%2Fb/copy/a%2Fb", {"page": 2}),
        )
        self.assertEqual(params, {"id": "a/b", "page": 2})

    async def testHttpSchemeRecognitionIgnoresCaseAndPreservesTheRemainder(
        self,
    ) -> None:
        """Preserve URL components while recognizing HTTP schemes regardless of case.

        Returns
        -------
        None
            No return value.
        """
        app = MagicMock()
        app.make = AsyncMock(
            return_value=SimpleNamespace(baseUrl="https://origin.test"),
        )
        ordinary, secure = _global_url(app), _global_secure_url(app)
        cases = (
            (
                "HTTP://EXAMPLE.test/PaTh?Q=MiXeD#Frag",
                "https://EXAMPLE.test/PaTh?Q=MiXeD#Frag",
            ),
            (
                "hTtP://EXAMPLE.test:8080/A%2fb?X=Y#Frag",
                "https://EXAMPLE.test:8080/A%2fb?X=Y#Frag",
            ),
            ("HTTPS://CDN.test/%2F?Case=YES#Top", "HTTPS://CDN.test/%2F?Case=YES#Top"),
            ("hTtPs://CDN.test/SomePath", "hTtPs://CDN.test/SomePath"),
        )
        for original, expected_secure in cases:
            with self.subTest(helper="url", url=original):
                app.make.reset_mock()
                self.assertEqual(await ordinary(original), original)
                app.make.assert_not_awaited()
            with self.subTest(helper="secure_url", url=original):
                app.make.reset_mock()
                self.assertEqual(await secure(original), expected_secure)
                app.make.assert_not_awaited()
        with self.subTest(helper="secure_url", source="request origin"):
            app.make.return_value = SimpleNamespace(baseUrl="HTTP://Origin.test:8080")
            self.assertEqual(await secure("/Page"), "https://Origin.test:8080/Page")

        file = MagicMock()
        file.url = AsyncMock()
        disk, storage = MagicMock(), MagicMock()
        disk.file.return_value = file
        storage.disk.return_value = disk
        app.make = AsyncMock(return_value=storage)
        asset = _global_secure_asset(app)
        for original, expected_secure in (
            *cases,
            ("//CDN.test/Asset", "https://CDN.test/Asset"),
        ):
            with self.subTest(helper="secure_asset", url=original):
                file.url.return_value = original
                self.assertEqual(await asset("style.css"), expected_secure)
        for unchanged in (
            "/relative/HTTP/path",
            "asset.svg",
            "FTP://Host.test/Path",
            "mailto:User@example.test",
        ):
            with self.subTest(helper="secure rewrite", unchanged=unchanged):
                self.assertEqual(_to_secure_url(unchanged), unchanged)
