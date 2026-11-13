# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Exercise bytecode filenames, loading failures and public annotations."""

import inspect
import ntpath
from pathlib import Path, PureWindowsPath
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import AsyncMock, patch

import jinja2

from orionis.support.concurrency import WorkQueueFullError
from orionis.test import TestCase
from orionis.view._failures import capture_service_failure
from orionis.view.cache import OrionisBytecodeCache
from orionis.view.contracts.engine import IViewEngine
from orionis.view.contracts.environment import IViewEnvironment
from orionis.view.engine import Jinja2Engine
from orionis.view.environment import ViewEnvironment
from orionis.view.exceptions import ViewRenderException, ViewTemplateNotFoundException


class TestViewEngineRegressions(TestCase):
    """Preserve loading boundaries and keep bytecode inside its directory."""

    async def testBytecodeNamesRemainPortableCacheBasenames(self) -> None:
        """
        Compile unusual loader names without changing the cache directory.

        Returns
        -------
        None
            No return value.
        """
        directory = Path(self.enterContext(TemporaryDirectory()))
        cache = OrionisBytecodeCache(str(directory))
        names = (
            "C:/page.html",
            "folder/report:2026.html",
            "CON.html",
            "AUX.html",
            "folder/notes?.html",
            "folder/a<b>|c*.html",
        )
        environment = jinja2.Environment(
            loader=jinja2.DictLoader(dict.fromkeys(names, "{{ value }}")),
            autoescape=True,
            enable_async=True,
            bytecode_cache=cache,
        )
        for name in names:
            with self.subTest(name=name):
                key = cache.getCacheKey(name)
                # Check the lexical boundary before any filesystem operation.
                root = PureWindowsPath("Z:/owned-cache")
                self.assertEqual((root / f"{key}.cache").parent, root)
                self.assertFalse(ntpath.isreserved(f"{key}.cache"))
                template = environment.get_template(name)
                self.assertEqual(await template.render_async(value="ready"), "ready")
                environment.cache.clear()
                with patch.object(environment, "compile", side_effect=AssertionError):
                    loaded = environment.get_template(name)
                self.assertEqual(await loaded.render_async(value="cached"), "cached")
                self.assertTrue((directory / f"{key}.cache").is_file())

    async def testLoadingSyntaxErrorsPreserveTheJinjaCause(self) -> None:
        """
        Wrap a real compiler failure at the engine boundary exactly once.

        Returns
        -------
        None
            No return value.
        """
        environment = jinja2.Environment(
            loader=jinja2.DictLoader({"broken.html": "{% if %}"}),
            autoescape=True,
            enable_async=True,
        )
        engine = Jinja2Engine(SimpleNamespace(getJinjaEnvironment=lambda: environment))
        with self.assertRaises(ViewRenderException) as caught:
            await engine.render("broken", {})
        self.assertIsInstance(caught.exception.__cause__, jinja2.TemplateSyntaxError)
        self.assertEqual(caught.exception.__cause__.name, "broken.html")

    async def testLoadingKeepsMissingAndAdmissionFailuresDistinct(self) -> None:
        """
        Preserve missing-template conversion and unrelated admission failures.

        Returns
        -------
        None
            No return value.
        """
        environment = jinja2.Environment(
            loader=jinja2.DictLoader({}),
            autoescape=True,
            enable_async=True,
        )
        engine = Jinja2Engine(SimpleNamespace(getJinjaEnvironment=lambda: environment))
        with self.assertRaises(ViewTemplateNotFoundException) as caught:
            await engine.render("missing", {})
        self.assertIsInstance(caught.exception.__cause__, jinja2.TemplateNotFound)
        for error in (WorkQueueFullError("queue full"), OSError("loader failure")):
            with (
                self.subTest(error=type(error).__name__),
                patch(
                    "orionis.view.engine._TEMPLATE_WORKERS.run",
                    AsyncMock(side_effect=error),
                ),
                self.assertRaises(type(error)) as admission,
            ):
                await engine.render("missing", {})
            self.assertIs(admission.exception, error)

    async def testAnnotationsResolveWithoutCallerNamespaces(self) -> None:
        """
        Resolve runtime annotations and preserve the optional async warmup hook.

        Returns
        -------
        None
            No return value.
        """
        for cls in (
            OrionisBytecodeCache,
            Jinja2Engine,
            ViewEnvironment,
            IViewEngine,
            IViewEnvironment,
        ):
            for name, member in vars(cls).items():
                method = member.__func__ if isinstance(member, staticmethod) else member
                if inspect.isfunction(method):
                    with self.subTest(owner=cls.__name__, method=name):
                        get_type_hints(method)
        get_type_hints(capture_service_failure)

        self.assertTrue(inspect.iscoroutinefunction(IViewEngine.warmup))
        self.assertNotIn("warmup", IViewEngine.__abstractmethods__)
        environment = jinja2.Environment(
            loader=jinja2.DictLoader({}),
            autoescape=True,
            enable_async=True,
        )
        engine = Jinja2Engine(SimpleNamespace(getJinjaEnvironment=lambda: environment))
        with patch.object(environment, "get_template", side_effect=AssertionError):
            self.assertIsNone(await IViewEngine.warmup(engine, "missing"))
