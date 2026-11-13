# ruff: noqa: PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Refresh reflected dependencies and invocation plans after explicit invalidation."""

import inspect

from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.introspection.callables.reflection import ReflectionCallable
from orionis.test import TestCase


class _FirstDependency:
    """Identify the original type annotation on an injectable parameter."""


class _SecondDependency:
    """Identify the replacement type annotation on the same parameter."""


class TestCacheInvalidation(TestCase):
    """Invalidate public reflection data after deliberately changing a callable."""

    def setUp(self) -> None:
        """Create an independent container outside the runner's active scope."""
        super().setUp()
        token = ScopedContext.setCurrentScope(None)
        self.addCleanup(ScopedContext.reset, token)
        container_type = type("CacheContainer", (Container,), {})
        self.container = container_type()
        self.addCleanup(Container._instances.pop, container_type, None)

    async def testClearCacheRefreshesDefaultsAndExplicitSignatures(self) -> None:
        """Refresh dependency defaults and invocation plans after signature changes."""
        for mutation in ("defaults", "signature"):
            with self.subTest(mutation=mutation):

                def target(value: int = 1) -> int:
                    """Return the value provided through the reflected parameter.

                    Parameters
                    ----------
                    value : int
                        Explicit argument or the current default value.

                    Returns
                    -------
                    int
                        Supplied value.
                    """
                    return value

                reflection = ReflectionCallable(target)
                self.assertEqual(
                    reflection.getDependencies().ordered["value"].default,
                    1,
                )
                self.assertEqual(await self.container.invoke(target), 1)
                if mutation == "defaults":
                    target.__defaults__ = (2,)
                else:
                    signature = inspect.signature(target)
                    parameter = signature.parameters["value"].replace(default=2)
                    target.__signature__ = signature.replace(parameters=[parameter])
                reflection.clearCache()
                self.assertEqual(
                    reflection.getSignature().parameters["value"].default,
                    2,
                )
                with self.subTest(consumer="reflection"):
                    self.assertEqual(
                        reflection.getDependencies().ordered["value"].default,
                        2,
                    )
                with self.subTest(consumer="container"):
                    self.assertEqual(await self.container.invoke(target), 2)

    async def testClearCacheRefreshesRuntimeDependencyAnnotations(self) -> None:
        """Inject the replacement type after clearing the callable's cached metadata."""

        def target(value: _FirstDependency) -> object:
            """Return the dependency selected by the active parameter annotation.

            Parameters
            ----------
            value : _FirstDependency
                Dependency supplied before the annotation is changed.

            Returns
            -------
            object
                Supplied dependency instance.
            """
            return value

        first = _FirstDependency()
        second = _SecondDependency()
        self.container.instance(_FirstDependency, first)
        self.container.instance(_SecondDependency, second)
        reflection = ReflectionCallable(target)
        self.assertIs(
            reflection.getDependencies().ordered["value"].type,
            _FirstDependency,
        )
        self.assertIs(await self.container.invoke(target), first)

        target.__annotations__["value"] = _SecondDependency
        reflection.clearCache()

        with self.subTest(consumer="reflection"):
            self.assertIs(
                reflection.getDependencies().ordered["value"].type,
                _SecondDependency,
            )
        with self.subTest(consumer="container"):
            self.assertIs(await self.container.invoke(target), second)
