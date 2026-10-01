from __future__ import annotations
import inspect
from abc import ABC
from orionis.container.container import Container
from orionis.container.contracts.container import IContainer
from orionis.test import TestCase

_ABSTRACT_METHODS = frozenset({
    "instance", "transient", "singleton", "scoped",
    "bound", "beginScope", "getCurrentScope",
    "make", "build", "invoke", "call",
})

class _ConcreteContainer(IContainer):
    """Minimal IContainer implementation used for structural tests."""

    def instance(self, _abstract, _instance, *, _alias=None, _override=False):
        """Register an instance in the container test double.

        Parameters
        ----------
        _abstract : object
            Value supplied for ``_abstract``.
        _instance : object
            Value supplied for ``_instance``.
        _alias : object
            Value supplied for ``_alias``.
        _override : object
            Value supplied for ``_override``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return True

    def transient(self, _abstract, _concrete, *, _alias=None, _override=False):
        """Register a transient service in the container test double.

        Parameters
        ----------
        _abstract : object
            Value supplied for ``_abstract``.
        _concrete : object
            Value supplied for ``_concrete``.
        _alias : object
            Value supplied for ``_alias``.
        _override : object
            Value supplied for ``_override``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return True

    def singleton(self, _abstract, _concrete, *, _alias=None, _override=False):
        """Register a singleton in the container test double.

        Parameters
        ----------
        _abstract : object
            Value supplied for ``_abstract``.
        _concrete : object
            Value supplied for ``_concrete``.
        _alias : object
            Value supplied for ``_alias``.
        _override : object
            Value supplied for ``_override``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return True

    def scoped(self, _abstract, _concrete, *, _alias=None, _override=False):
        """Register a scoped service in the container test double.

        Parameters
        ----------
        _abstract : object
            Value supplied for ``_abstract``.
        _concrete : object
            Value supplied for ``_concrete``.
        _alias : object
            Value supplied for ``_alias``.
        _override : object
            Value supplied for ``_override``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return True

    def bound(self, _key):
        """Check whether a service key is bound.

        Parameters
        ----------
        _key : object
            Value supplied for ``_key``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return False

    def beginScope(self):
        """Start a scope in the container test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return

    def getCurrentScope(self):
        """Return the active scope from the container test double.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return

    async def make(self, _key, *_args: object, **_kwargs: object):
        """Resolve a service through the container test double.

        Parameters
        ----------
        _key : object
            Value supplied for ``_key``.
        *_args : object
            Arguments passed to the wrapped callable.
        **_kwargs : object
            Arguments passed to the wrapped callable.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return

    async def build(self, _target, *_args: object, **_kwargs: object):
        """Build a service through the container test double.

        Parameters
        ----------
        _target : object
            Value supplied for ``_target``.
        *_args : object
            Arguments passed to the wrapped callable.
        **_kwargs : object
            Arguments passed to the wrapped callable.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return

    async def invoke(self, _fn, *_args: object, **_kwargs: object):
        """Invoke a callable through the container test double.

        Parameters
        ----------
        _fn : object
            Value supplied for ``_fn``.
        *_args : object
            Arguments passed to the wrapped callable.
        **_kwargs : object
            Arguments passed to the wrapped callable.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return

    async def call(self, _instance, _name, *_args: object, **_kwargs: object):
        """Call a named method through the container test double.

        Parameters
        ----------
        _instance : object
            Value supplied for ``_instance``.
        _name : object
            Value supplied for ``_name``.
        *_args : object
            Arguments passed to the wrapped callable.
        **_kwargs : object
            Arguments passed to the wrapped callable.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return

class TestIContainer(TestCase):

    def testContractIsAnAbstractBaseClass(self) -> None:
        """
        Declare IContainer as an ABC that cannot be instantiated directly.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertTrue(issubclass(IContainer, ABC))
        with self.assertRaises(TypeError):
            IContainer()  # type: ignore[abstract]

    def testContractDeclaresExactlyTheExpectedAbstractMethods(self) -> None:
        """
        Declare exactly the documented set of abstract methods.

        Catches both silent removals and unintended additions to the public
        container surface.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertEqual(IContainer.__abstractmethods__, _ABSTRACT_METHODS)

    def testConcreteSubclassCanBeInstantiated(self) -> None:
        """
        Instantiate a subclass that implements every abstract method.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsInstance(_ConcreteContainer(), IContainer)

    def testContainerImplementationMatchesTheContractSignatures(self) -> None:
        """
        Keep the Container parameter names aligned with the contract.

        Only parameter names are compared: the contract module defers its
        annotations while the implementation does not, so the resolved
        annotation objects can never be equal.

        Returns
        -------
        None
            This method does not return a value.
        """
        for name in sorted(_ABSTRACT_METHODS):
            expected = list(
                inspect.signature(getattr(IContainer, name)).parameters,
            )
            actual = list(
                inspect.signature(getattr(Container, name)).parameters,
            )
            self.assertEqual(actual, expected, f"signature drift on {name!r}")

    def testAsynchronousContractMethodsStayAsynchronous(self) -> None:
        """
        Keep the resolution entry points declared as coroutine functions.

        Returns
        -------
        None
            This method does not return a value.
        """
        for name in ("make", "build", "invoke", "call"):
            self.assertTrue(
                inspect.iscoroutinefunction(getattr(Container, name)),
                f"{name!r} must stay asynchronous",
            )
