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

class _OtherDependency:
    """Second instance registered for constructor injection."""

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

class _NeedsTwoDependencies:
    """Require two dependencies under postponed evaluation."""

    def __init__(
        self,
        first: _Dependency,
        second: _OtherDependency,
    ) -> None:
        """Store both resolved dependencies.

        Parameters
        ----------
        first : _Dependency
            First injected service.
        second : _OtherDependency
            Second injected service.
        """
        self.first = first
        self.second = second

class _NeedsKnownAndUnknown:
    """Require one known and one unresolved postponed type."""

    def __init__(
        self,
        first: _Dependency,
        second: UnknownDependency,
    ) -> None:
        """Store the two supplied dependencies.

        Parameters
        ----------
        first : _Dependency
            Known service.
        second : UnknownDependency
            Intentionally undefined type.
        """
        self.first = first
        self.second = second

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

    async def testBuildInjectsMultipleDeferredConstructorTypes(self) -> None:
        """Resolve all known constructor references into registered types."""
        first = _Dependency()
        second = _OtherDependency()
        self.container.instance(None, first)
        self.container.instance(None, second)

        built = await self.container.build(_NeedsTwoDependencies)

        self.assertIs(built.first, first)
        self.assertIs(built.second, second)

    def testUnknownReferencePreservesOtherResolvedHints(self) -> None:
        """Resolve known hints when another constructor hint is unavailable."""
        plan = constructor_plan(
            _NeedsKnownAndUnknown,
            _NeedsKnownAndUnknown.__init__,
        )

        self.assertIs(plan.arguments[0].type, _Dependency)
        self.assertIs(plan.arguments[1].type, str)

    def testClassLocalReferencePreservesOtherResolvedHints(self) -> None:
        """Resolve a local self reference alongside a module-level service."""

        class LocalSelf:
            """Refer to its own class in a deferred constructor hint."""

            def __init__(
                self,
                known: _Dependency,
                self_ref: LocalSelf,
            ) -> None:
                """Store both declared dependencies.

                Parameters
                ----------
                known : _Dependency
                    Module-level dependency.
                self_ref : LocalSelf
                    Class-local dependency.
                """
                self.known = known
                self.self_ref = self_ref

        plan = constructor_plan(LocalSelf, LocalSelf.__init__)

        self.assertIs(plan.arguments[0].type, _Dependency)
        self.assertIs(plan.arguments[1].type, LocalSelf)

    async def testUnknownReferenceDoesNotInjectRegisteredString(self) -> None:
        """Reject an unknown hint even when a string service is registered."""
        self.container.instance(None, "string service")

        with self.assertRaisesRegex(TypeError, "Cannot resolve forward reference"):
            await self.container.build(_NeedsUnknown)

    async def testSelfReferenceStillRaisesCircularDependency(self) -> None:
        """Leave the container's cycle guard in control of self references.

        Returns
        -------
        None
            Construction raises the existing circular dependency error.
        """
        with self.assertRaises(CircularDependencyException):
            await self.container.build(_Circular)
