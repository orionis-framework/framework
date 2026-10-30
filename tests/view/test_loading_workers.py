import asyncio
import threading
from types import SimpleNamespace
from typing import TYPE_CHECKING, Self
from unittest.mock import patch
import jinja2
from orionis.test import TestCase
from orionis.view.engine import Jinja2Engine

if TYPE_CHECKING:
    from collections.abc import Callable

class TestTemplateWorkers(TestCase):
    """Verify that synchronous cold loaders run away from the application loop."""

    async def testColdWarmAndReloadPaths(self: Self) -> None:
        """
        Prepare templates without rendering globals or resubmitting hot loads.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        caller = threading.get_ident()
        threads = []
        calls = []

        class Loader(jinja2.DictLoader):
            def get_source(
                self: Self, environment: jinja2.Environment, template: str,
            ) -> tuple[str, None, Callable[[], bool]]:
                """
                Record the loading thread and delegate to the dictionary loader.

                Parameters
                ----------
                environment : jinja2.Environment
                    Jinja environment requesting the template source.
                template : str
                    Template identifier stored in the dictionary loader.

                Returns
                -------
                tuple[str, None, Callable[[], bool]]
                    Template source, absent filename and freshness callback.
                """
                threads.append(threading.get_ident())
                return super().get_source(environment, template)

        environment = jinja2.Environment(
            autoescape=True,
            loader=Loader({"page.html": "{{ value() }}"}),
            enable_async=True,
            auto_reload=False,
        )
        engine = Jinja2Engine(SimpleNamespace(getJinjaEnvironment=lambda: environment))

        async def value() -> str:
            """
            Record the rendering thread and return the template value.

            Returns
            -------
            str
                Template value produced after yielding to the event loop.
            """
            calls.append(threading.get_ident())
            await asyncio.sleep(0)
            return "ready"

        environment.globals["value"] = value
        await engine.warmup("page")
        self.assertEqual(calls, [])
        self.assertTrue(threads and all(thread != caller for thread in threads))
        with patch(
            "orionis.view.engine._TEMPLATE_WORKERS.run",
            side_effect=AssertionError,
        ):
            self.assertEqual(await engine.render("page", {}), "ready")
        self.assertEqual(calls, [caller])
        environment.auto_reload = True
        environment.loader.mapping["page.html"] = "updated"
        self.assertEqual(await engine.render("page", {}), "updated")
