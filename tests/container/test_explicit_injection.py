from __future__ import annotations
from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.schemas.schema import Schema
from orionis.test import TestCase

class _Dependency:
    """Represent a service that can be passed or injected."""

class _NeedsDependency:
    """Receive a service during construction."""

    def __init__(self, dependency: _Dependency) -> None:
        """Store the supplied service.

        Parameters
        ----------
        dependency : _Dependency
            Service to store.
        """
        self.dependency = dependency

class _Payload(Schema):
    """Represent a request payload that may be supplied explicitly."""

    value: int

class _NeedsPayload:
    """Receive a payload during construction."""

    def __init__(self, payload: _Payload) -> None:
        """Store the supplied payload.

        Parameters
        ----------
        payload : _Payload
            Validated request payload.
        """
        self.payload = payload

class _Action:
    """Expose a service-dependent controller action."""

    def handle(self, dependency: _Dependency) -> _Dependency:
        """Return the supplied service.

        Parameters
        ----------
        dependency : _Dependency
            Service provided by the caller or container.

        Returns
        -------
        _Dependency
            Selected service.
        """
        return dependency

class _NamedArguments:
    """Expose parameters with names often used for variadic arguments."""

    def handle(
        self,
        args: _Dependency,
        *,
        kwargs: _Dependency,
    ) -> tuple[_Dependency, _Dependency]:
        """Return dependencies named like variadic parameters.

        Parameters
        ----------
        args : _Dependency
            Positional service.
        kwargs : _Dependency
            Keyword-only service.

        Returns
        -------
        tuple[_Dependency, _Dependency]
            Both injected services.
        """
        return args, kwargs

class TestExplicitInjection(TestCase):
    """Preserve caller arguments in the presence of dependency bindings."""

    def setUp(self) -> None:
        """Create a container without an inherited request scope."""
        self.token = ScopedContext.setCurrentScope(None)
        self.container = object.__new__(Container)
        Container.__init__(self.container)

    def tearDown(self) -> None:
        """Restore the request scope active before the test."""
        ScopedContext.reset(self.token)

    async def testExplicitConstructorArgumentWinsOverBinding(self) -> None:
        """Use an explicit positional service in a bound constructor."""
        bound = _Dependency()
        explicit = _Dependency()
        self.container.instance(None, bound)

        built = await self.container.build(_NeedsDependency, explicit)

        self.assertIs(built.dependency, explicit)

    async def testExplicitActionArgumentWinsOverBinding(self) -> None:
        """Use an explicit positional service in a bound action."""
        bound = _Dependency()
        explicit = _Dependency()
        self.container.instance(None, bound)

        result = await self.container.call(_Action(), "handle", explicit)

        self.assertIs(result, explicit)

    async def testExplicitPayloadSkipsRequestResolution(self) -> None:
        """Use a supplied schema without resolving a request service."""
        payload = _Payload(value=7)

        built = await self.container.build(_NeedsPayload, payload)

        self.assertIs(built.payload, payload)

    async def testExplicitDependencySkipsDeferredProvider(self) -> None:
        """Avoid starting a provider for a caller-supplied dependency."""
        path = f"{_Dependency.__module__}.{_Dependency.__name__}"
        self.container._deferred_providers[path] = {
            "module": "missing_provider_module",
            "class": "MissingProvider",
        }
        explicit = _Dependency()

        built = await self.container.build(_NeedsDependency, explicit)

        self.assertIs(built.dependency, explicit)

    async def testUnhashableBuildTargetGetsClassError(self) -> None:
        """Reject an invalid build target before dictionary lookups."""
        with self.assertRaisesRegex(TypeError, "expects a class type"):
            await self.container.build([])

    async def testNamedArgsAndKwargsRemainInjectable(self) -> None:
        """Inject ordinary parameters named args and kwargs."""
        shared = _Dependency()
        self.container.instance(None, shared)

        result = await self.container.call(_NamedArguments(), "handle")

        self.assertEqual(result, (shared, shared))
