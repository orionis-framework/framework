# ruff: noqa: PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Keep dependency-cycle detection isolated between container instances."""

from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.test import TestCase


class _FirstContainer(Container):
    """Own the service whose dependency needs a deferred provider."""


class _SecondContainer(Container):
    """Build the same service type with independent explicit dependencies."""


class _Dependency:
    """Identify distinct values belonging to the two service graphs."""


class _Service:
    """Retain the dependency supplied by its owning container."""

    def __init__(self, dependency: _Dependency) -> None:
        """Store the dependency resolved for this service graph.

        Parameters
        ----------
        dependency : _Dependency
            Value owned by this particular service instance.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.dependency = dependency


class _DependencyProvider:
    """Initialize another container while the first service graph is pending."""

    def register(self) -> None:
        """Publish the first container's dependency.

        Returns
        -------
        None
            This method does not return a value.
        """
        _FirstContainer().instance(_Dependency, _Dependency())

    async def boot(self) -> None:
        """Build an independent service graph with an explicit dependency.

        Returns
        -------
        None
            This method does not return a value.
        """
        other = _SecondContainer()
        service = await other.build(_Service, _Dependency())
        other.instance(_Service, service)


class TestResolutionContext(TestCase):
    """Exercise nested public resolutions belonging to distinct containers."""

    async def testIndependentContainerDoesNotInheritAFalseDependencyCycle(self) -> None:
        """Build the same type in another container during deferred provider boot."""
        token = ScopedContext.setCurrentScope(None)
        self.addCleanup(ScopedContext.reset, token)
        for container_type in (_FirstContainer, _SecondContainer):
            self.addCleanup(Container._instances.pop, container_type, None)
        first = _FirstContainer()
        first._deferred_providers = {
            f"{_Dependency.__module__}.{_Dependency.__name__}": {
                "module": __name__,
                "class": "_DependencyProvider",
            },
        }

        resolved = await first.build(_Service)
        other = await _SecondContainer().make(_Service)

        self.assertIsInstance(resolved, _Service)
        self.assertIsInstance(other, _Service)
        self.assertIsNot(resolved, other)
        self.assertIs(resolved.dependency, await first.make(_Dependency))
        self.assertIsNot(resolved.dependency, other.dependency)
