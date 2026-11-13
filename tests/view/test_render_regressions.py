# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Preserve native rendering failures and reflective view contracts."""

import inspect
from typing import get_type_hints
import jinja2
from orionis.test import TestCase
from orionis.support.concurrency import WorkQueueFullError
from orionis.view.contracts.factory import IViewFactory
from orionis.view.engine import Jinja2Engine
from orionis.view.exceptions import ViewRenderException
from orionis.view.factory import ViewFactory
from orionis.view.pending import PendingView
from orionis.view.provider import ViewServiceProvider
from tests.view.test_pending import _StubEngine


class _MemoryEnvironment:
    """Provide a real strict Jinja environment with one invalid expression."""

    def __init__(self) -> None:
        """Build an isolated asynchronous template environment.

        Returns
        -------
        None
            No return value.
        """
        self.environment = jinja2.Environment(
            loader=jinja2.DictLoader({"broken.html": "{{ unknown.name }}"}),
            enable_async=True,
            autoescape=True,
            undefined=jinja2.StrictUndefined,
        )

    def getJinjaEnvironment(self) -> jinja2.Environment:
        """Return the isolated native rendering environment.

        Returns
        -------
        jinja2.Environment
            Environment containing the controlled invalid expression.
        """
        return self.environment


class TestViewRenderRegressions(TestCase):
    """Keep original failure causes and runtime annotations available."""

    async def testTemplateWorkerOverloadKeepsItsPublicType(self) -> None:
        """Propagate native worker saturation through the deferred response.

        Returns
        -------
        None
            No return value.
        """
        original = WorkQueueFullError("The controlled template queue is full.")
        factory = ViewFactory(_StubEngine(error=original))
        with self.assertRaises(WorkQueueFullError) as raised:
            await factory.make("busy")
        self.assertIs(raised.exception, original)

    async def testNativeTemplateFailureIsWrappedOnlyOnce(self) -> None:
        """Keep Jinja's native failure as the direct rendering error cause.

        Returns
        -------
        None
            No return value.
        """
        factory = ViewFactory(Jinja2Engine(_MemoryEnvironment()))
        with self.assertRaises(ViewRenderException) as raised:
            await factory.make("broken")
        self.assertIsInstance(raised.exception.__cause__, jinja2.UndefinedError)

    def testViewAnnotationsResolveWithoutCallerNamespaces(self) -> None:
        """Resolve factory and deferred response types through native reflection.

        Returns
        -------
        None
            No return value.
        """
        for target in (IViewFactory, ViewFactory, PendingView, ViewServiceProvider):
            for name, function in vars(target).items():
                if inspect.isfunction(function):
                    with self.subTest(target=target.__name__, method=name):
                        self.assertIn("return", get_type_hints(function))
