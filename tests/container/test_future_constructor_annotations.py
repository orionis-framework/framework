from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.container.entities.invocation import constructor_plan
from orionis.container.exceptions import CircularDependencyException
from orionis.test import TestCase

if TYPE_CHECKING:
    class UnknownDependency:
        """Type deliberately unavailable when constructor hints resolve."""

class _Dependency:
    """Instance registered for constructor injection."""

class _NeedsDependency:
    """Require a dependency annotated under postponed evaluation."""

    def __init__(self, dependency: _Dependency) -> None:
        """Store the resolved dependency.

        Parameters
        ----------
        dependency : _Dependency
            Instance supplied by the container.

        Returns
        -------
        None
            Store the dependency supplied by the container.
        """
        self.dependency = dependency

class _NeedsUnknown:
    """Carry an unresolved forward reference for compatibility testing."""

    def __init__(self, dependency: UnknownDependency) -> None:
        """Receive an unresolved dependency.

        Parameters
        ----------
        dependency : UnknownDependency
            Intentionally undefined type.

        Returns
        -------
        None
            Store the unresolved dependency value.
        """
        self.dependency = dependency

class _Circular:
    """Refer to itself through a postponed constructor annotation."""

    def __init__(self, dependency: _Circular) -> None:
        """Receive the circular dependency.

        Parameters
        ----------
        dependency : _Circular
            Same class currently being constructed.

        Returns
        -------
        None
            Store the circular dependency value.
        """
        self.dependency = dependency

class TestFutureConstructorAnnotations(TestCase):
    """Resolve deferred constructor types without changing fallback behavior."""

    def setUp(self) -> None:
        """Create an isolated container outside the runner's scope.

        Returns
        -------
        None
            The container is ready for registrations.
        """
        self.token = ScopedContext.setCurrentScope(None)
        self.container = object.__new__(Container)
        Container.__init__(self.container)

    def tearDown(self) -> None:
        """Restore the caller's scope.

        Returns
        -------
        None
            The original scope is active again.
        """
        ScopedContext.reset(self.token)

    async def testBuildInjectsRegisteredDeferredConstructorType(self) -> None:
        """Resolve a string annotation to the registered runtime class.

        Returns
        -------
        None
            The built object receives the exact registered instance.
        """
        provided = _Dependency()
        self.container.instance(None, provided)

        built = await self.container.build(_NeedsDependency)

        self.assertIs(built.dependency, provided)
        plan = constructor_plan(_NeedsDependency, _NeedsDependency.__init__)
        self.assertIs(plan.arguments[0].type, _Dependency)

    def testUnknownDeferredTypeKeepsPreviousMetadata(self) -> None:
        """Keep the generic reflection result for unknown references.

        Returns
        -------
        None
            Existing metadata remains available without a new error.
        """
        plan = constructor_plan(_NeedsUnknown, _NeedsUnknown.__init__)

        self.assertIs(plan.arguments[0].type, str)
        self.assertEqual(plan.arguments[0].class_name, "UnknownDependency")

    async def testSelfReferenceStillRaisesCircularDependency(self) -> None:
        """Leave the container's cycle guard in control of self references.

        Returns
        -------
        None
            Construction raises the existing circular dependency error.
        """
        with self.assertRaises(CircularDependencyException):
            await self.container.build(_Circular)
