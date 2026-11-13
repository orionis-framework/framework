# ruff: noqa: ARG003, PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from abc import ABC
from inspect import isabstract, signature
from typing import Any
from orionis.environment import Env
from orionis.environment.contracts.env import IEnv
from orionis.environment.enums.value_type import EnvironmentValueType
from orionis.test import TestCase

# Abstract surface the contract is expected to publish.
_EXPECTED_ABSTRACTS: frozenset[str] = frozenset(
    {"get", "set", "unset", "all", "reload"},
)

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _CompleteEnv(IEnv):
    """Minimal implementation covering the whole contract."""

    __slots__ = ()

    @classmethod
    def get(cls, key: str, default: object | None = None) -> object:
        """Return the supplied default for every key.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.
        default : object | None
            Value supplied for ``default``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return default

    @classmethod
    def set(
        cls,
        key: str,
        value: object,
        type_hint: str | EnvironmentValueType | None = None,
        *,
        only_os: bool = False,
    ) -> bool:
        """Pretend the assignment always succeeds.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.
        value : object
            Value supplied for ``value``.
        type_hint : str | EnvironmentValueType | None
            Value supplied for ``type_hint``.
        only_os : bool
            Value supplied for ``only_os``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return True

    @classmethod
    def unset(cls, key: str, *, only_os: bool = False) -> bool:
        """Pretend the removal always succeeds.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.
        only_os : bool
            Value supplied for ``only_os``.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return True

    @classmethod
    def all(cls) -> dict[str, Any]:
        """Return an empty mapping of variables.

        Returns
        -------
        dict[str, Any]
            Value produced by the helper.
        """
        return {}

    @classmethod
    def reload(cls) -> bool:
        """Pretend the reload always succeeds.

        Returns
        -------
        bool
            Value produced by the helper.
        """
        return True


class _IncompleteEnv(IEnv):
    """Implementation that deliberately leaves most methods unimplemented."""

    __slots__ = ()

    @classmethod
    def get(cls, key: str, default: object | None = None) -> object:
        """Return the supplied default for every key.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.
        default : object | None
            Value supplied for ``default``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return default


# ---------------------------------------------------------------------------
# TestEnvContract
# ---------------------------------------------------------------------------


class TestEnvContract(TestCase):
    def testIsAnAbstractBaseClass(self) -> None:
        """Expose the environment contract as an abstract base class.

        Validates that the contract cannot be used as a concrete service
        and participates in the ABC registration machinery.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(IEnv, ABC))
        self.assertTrue(isabstract(IEnv))

    def testPublishesExactlyTheDocumentedAbstractSurface(self) -> None:
        """Publish exactly the documented abstract method surface.

        Validates that no method is silently added to or removed from the
        contract without updating its implementations.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(IEnv.__abstractmethods__, _EXPECTED_ABSTRACTS)

    def testDeclaresEmptySlots(self) -> None:
        """Declare empty slots so implementations stay dictionary free.

        Validates that implementations declaring ``__slots__`` do not
        inherit an unwanted instance dictionary from the contract.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(IEnv.__dict__.get("__slots__"), ())

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Reject direct instantiation of the contract.

        Validates that callers are forced to depend on a concrete facade
        implementation instead of the interface itself.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            IEnv()

    def testRejectsPartialImplementations(self) -> None:
        """Reject subclasses that leave abstract methods unimplemented.

        Validates that a half-finished facade fails at construction time
        rather than at the first call site.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            _IncompleteEnv()

    def testAcceptsCompleteImplementations(self) -> None:
        """Accept subclasses that implement the whole contract.

        Validates that the abstract surface is satisfiable without any
        additional hook or attribute.

        Returns
        -------
        None
            No return value.
        """
        service = _CompleteEnv()
        self.assertEqual(service.get("KEY", "default"), "default")
        self.assertTrue(service.set("KEY", "value", EnvironmentValueType.STR))
        self.assertTrue(service.unset("KEY"))
        self.assertEqual(service.all(), {})
        self.assertTrue(service.reload())

    def testMatchesTheSignaturesOfTheImplementation(self) -> None:
        """Match the resolved signatures published by the shipped facade.

        Validates that ``Env`` can be substituted wherever the contract is
        expected without changing call sites.

        Returns
        -------
        None
            No return value.
        """
        for name in sorted(_EXPECTED_ABSTRACTS):
            with self.subTest(method=name):
                expected = signature(getattr(IEnv, name), eval_str=True)
                actual = signature(getattr(Env, name), eval_str=True)
                self.assertEqual(actual, expected)

    def testIsImplementedByTheShippedFacade(self) -> None:
        """Recognise the shipped facade as a valid implementation.

        Validates that ``Env`` actually derives from the contract used
        across the framework.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(Env, IEnv))
        self.assertEqual(Env.__abstractmethods__, frozenset())
