# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
import inspect
from abc import ABC
from orionis.container.container import Container
from orionis.container.contracts.container import IContainer
from orionis.test import TestCase

_ABSTRACT_METHODS = frozenset(
    {
        "instance",
        "transient",
        "singleton",
        "scoped",
        "bound",
        "beginScope",
        "getCurrentScope",
        "make",
        "build",
        "invoke",
        "call",
    },
)


class _ConcreteContainer(IContainer):
    """Minimal IContainer implementation used for structural tests."""

    def instance(
        self,
        _abstract: object,
        _instance: object,
        *,
        _alias: str | None = None,
        _override: bool = False,
    ) -> bool:
        """Register an instance in the container test double.

        Parameters
        ----------
        _abstract : object
            Value supplied for ``_abstract``.
        _instance : object
            Value supplied for ``_instance``.
        _alias : str | None
            Value supplied for ``_alias``.
        _override : bool
            Value supplied for ``_override``.

        Returns
        -------
        bool
            Fixed result supplied by this structural fixture.
        """
        return True

    def transient(
        self,
        _abstract: object,
        _concrete: object,
        *,
        _alias: str | None = None,
        _override: bool = False,
    ) -> bool:
        """Register a transient service in the container test double.

        Parameters
        ----------
        _abstract : object
            Value supplied for ``_abstract``.
        _concrete : object
            Value supplied for ``_concrete``.
        _alias : str | None
            Value supplied for ``_alias``.
        _override : bool
            Value supplied for ``_override``.

        Returns
        -------
        bool
            Fixed result supplied by this structural fixture.
        """
        return True

    def singleton(
        self,
        _abstract: object,
        _concrete: object,
        *,
        _alias: str | None = None,
        _override: bool = False,
    ) -> bool:
        """Register a singleton in the container test double.

        Parameters
        ----------
        _abstract : object
            Value supplied for ``_abstract``.
        _concrete : object
            Value supplied for ``_concrete``.
        _alias : str | None
            Value supplied for ``_alias``.
        _override : bool
            Value supplied for ``_override``.

        Returns
        -------
        bool
            Fixed result supplied by this structural fixture.
        """
        return True

    def scoped(
        self,
        _abstract: object,
        _concrete: object,
        *,
        _alias: str | None = None,
        _override: bool = False,
    ) -> bool:
        """Register a scoped service in the container test double.

        Parameters
        ----------
        _abstract : object
            Value supplied for ``_abstract``.
        _concrete : object
            Value supplied for ``_concrete``.
        _alias : str | None
            Value supplied for ``_alias``.
        _override : bool
            Value supplied for ``_override``.

        Returns
        -------
        bool
            Fixed result supplied by this structural fixture.
        """
        return True

    def bound(self, _key: object) -> bool:
        """Check whether a service key is bound.

        Parameters
        ----------
        _key : object
            Value supplied for ``_key``.

        Returns
        -------
        bool
            Fixed result supplied by this structural fixture.
        """
        return False

    def beginScope(self) -> None:
        """Provide the required scope hook for structural inspection.

        Returns
        -------
        None
            No return value.
        """
        return

    def getCurrentScope(self) -> None:
        """Report no active scope in the structural container fixture.

        Returns
        -------
        None
            No return value.
        """
        return

    async def make(self, _key: object, *_args: object, **_kwargs: object) -> None:
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
        None
            No return value.
        """
        return

    async def build(self, _target: object, *_args: object, **_kwargs: object) -> None:
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
        None
            No return value.
        """
        return

    async def invoke(self, _fn: object, *_args: object, **_kwargs: object) -> None:
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
        None
            No return value.
        """
        return

    async def call(
        self,
        _instance: object,
        _name: str,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        """Call a named method through the container test double.

        Parameters
        ----------
        _instance : object
            Value supplied for ``_instance``.
        _name : str
            Value supplied for ``_name``.
        *_args : object
            Arguments passed to the wrapped callable.
        **_kwargs : object
            Arguments passed to the wrapped callable.

        Returns
        -------
        None
            No return value.
        """
        return


class TestIContainer(TestCase):
    def testContractIsAnAbstractBaseClass(self) -> None:
        """
        Declare IContainer as an ABC that cannot be instantiated directly.

        Returns
        -------
        None
            No return value.
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
            No return value.
        """
        self.assertEqual(IContainer.__abstractmethods__, _ABSTRACT_METHODS)

    def testConcreteSubclassCanBeInstantiated(self) -> None:
        """
        Instantiate a subclass that implements every abstract method.

        Returns
        -------
        None
            No return value.
        """
        self.assertIsInstance(_ConcreteContainer(), IContainer)

    def testContainerImplementationMatchesTheContractSignatures(self) -> None:
        """Match runtime parameter kinds, defaults, annotations, and return types."""
        for name in sorted(_ABSTRACT_METHODS):
            with self.subTest(method=name):
                expected = inspect.signature(getattr(IContainer, name), eval_str=True)
                actual = inspect.signature(getattr(Container, name), eval_str=True)
                self.assertEqual(
                    [item for key, item in actual.parameters.items() if key != "self"],
                    [
                        item
                        for key, item in expected.parameters.items()
                        if key != "self"
                    ],
                )
                self.assertEqual(actual.return_annotation, expected.return_annotation)

    def testAsynchronousContractMethodsStayAsynchronous(self) -> None:
        """
        Keep the resolution entry points declared as coroutine functions.

        Returns
        -------
        None
            No return value.
        """
        for name in ("make", "build", "invoke", "call"):
            self.assertTrue(
                inspect.iscoroutinefunction(getattr(Container, name)),
                f"{name!r} must stay asynchronous",
            )
