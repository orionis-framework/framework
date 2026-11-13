# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect scoped overrides and Python call semantics during resolution."""

from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.test import TestCase


class _Service:
    """Identify a dependency whose global and scoped instances differ."""


class TestResolutionRegressions(TestCase):
    """Resolve public bindings without mutating the application's container."""

    def setUp(self) -> None:
        """Create a separate container subclass outside the runner's scope."""
        super().setUp()
        token = ScopedContext.setCurrentScope(None)
        self.addCleanup(ScopedContext.reset, token)
        container_type = type("_ResolutionContainer", (Container,), {})
        self.container = container_type()
        self.addCleanup(Container._instances.pop, container_type, None)

    async def testScopedInstancesOverrideWarmSingletonsOnlyInsideTheirScope(
        self,
    ) -> None:
        """Honor an explicit scoped instance through types, aliases and injection."""
        global_service = _Service()
        scoped_service = _Service()
        self.container.instance(_Service, global_service, alias="service")
        self.assertIs(await self.container.make(_Service), global_service)

        def receive(service: _Service) -> _Service:
            """Return the injected service.

            Parameters
            ----------
            service : _Service
                Instance selected by the active scope.

            Returns
            -------
            _Service
                The supplied service instance.
            """
            return service

        async with self.container.beginScope():
            self.container.instance(_Service, scoped_service)
            for key in (_Service, "service"):
                with self.subTest(key=key):
                    self.assertIs(await self.container.make(key), scoped_service)
            self.assertIs(await self.container.invoke(receive), scoped_service)
        self.assertIs(await self.container.make(_Service), global_service)
        self.assertIs(await self.container.make("service"), global_service)

    async def testPositionalOnlyNamesRemainAvailableToKeywordArguments(self) -> None:
        """Preserve Python's positional-only defaults and keyword rejection."""

        def capture(value: int = 3, /, **extras: object) -> tuple[int, dict]:
            """Return the positional-only value and unrelated keyword arguments.

            Parameters
            ----------
            value : int
                Positional-only value with a default.
            **extras : object
                Keywords including a name shared by the positional parameter.

            Returns
            -------
            tuple[int, dict]
                The positional value and captured keywords.
            """
            return value, extras

        def reject(value: int = 3, /) -> int:
            """Return the positional-only value without accepting keywords.

            Parameters
            ----------
            value : int
                Positional-only value with a default.

            Returns
            -------
            int
                Supplied positional value.
            """
            return value

        with self.subTest(operation="capture"):
            self.assertEqual(
                await self.container.invoke(capture, value=9),
                (3, {"value": 9}),
            )
        with self.subTest(operation="reject"), self.assertRaises(TypeError):
            await self.container.invoke(reject, value=9)

        class CapturedConstructor:
            """Retain a positional-only constructor argument and captured keywords."""

            def __init__(self, value: int = 3, /, **extras: object) -> None:
                """Record the values supplied by constructor injection.

                Parameters
                ----------
                value : int
                    Positional-only value with a default.
                **extras : object
                    Keywords including the positional-only parameter's name.
                """
                self.value = value
                self.extras = extras

        with self.subTest(operation="constructor"):
            result = await self.container.build(CapturedConstructor, value=9)
            self.assertEqual((result.value, result.extras), (3, {"value": 9}))

    async def testScopedPrimitiveInstancesParticipateInInjection(self) -> None:
        """Inject explicitly scoped primitives without requiring a global binding."""

        def positional(value: int) -> int:
            """Return a positional dependency supplied by the scope.

            Parameters
            ----------
            value : int
                Explicitly registered scoped integer.

            Returns
            -------
            int
                Injected integer value.
            """
            return value

        def keyword(*, value: int) -> int:
            """Return a keyword-only dependency supplied by the scope.

            Parameters
            ----------
            value : int
                Explicitly registered scoped integer.

            Returns
            -------
            int
                Injected integer value.
            """
            return value

        async with self.container.beginScope():
            self.container.instance(int, 7)
            for action in (positional, keyword):
                with self.subTest(action=action.__name__):
                    self.assertEqual(await self.container.invoke(action), 7)
