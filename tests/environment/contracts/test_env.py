from abc import ABC
from inspect import isabstract, signature
from typing import Any
from orionis.environment.contracts.env import IEnv
from orionis.environment.facade import Env
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

    # ruff: noqa: FBT001

    __slots__ = ()

    @classmethod
    def get(cls, key: str, default: object | None = None) -> object:
        """Return the supplied default for every key."""
        return default

    @classmethod
    def set(
        cls,
        key: str,
        value: str | float | bool | list | dict | tuple | set,
        type_hint: str | None = None,
        *,
        only_os: bool = False,
    ) -> bool:
        """Pretend the assignment always succeeds."""
        return True

    @classmethod
    def unset(cls, key: str, *, only_os: bool = False) -> bool:
        """Pretend the removal always succeeds."""
        return True

    @classmethod
    def all(cls) -> dict[str, Any]:
        """Return an empty mapping of variables."""
        return {}

    @classmethod
    def reload(cls) -> bool:
        """Pretend the reload always succeeds."""
        return True

class _IncompleteEnv(IEnv):
    """Implementation that deliberately leaves most methods unimplemented."""

    __slots__ = ()

    @classmethod
    def get(cls, key: str, default: object | None = None) -> object:
        """Return the supplied default for every key."""
        return default

# ---------------------------------------------------------------------------
# TestEnvContract
# ---------------------------------------------------------------------------

class TestEnvContract(TestCase):

    def testIsAnAbstractBaseClass(self) -> None:
        """
        Expose the environment contract as an abstract base class.

        Validates that the contract cannot be used as a concrete service
        and participates in the ABC registration machinery.
        """
        self.assertTrue(issubclass(IEnv, ABC))
        self.assertTrue(isabstract(IEnv))

    def testPublishesExactlyTheDocumentedAbstractSurface(self) -> None:
        """
        Publish exactly the documented abstract method surface.

        Validates that no method is silently added to or removed from the
        contract without updating its implementations.
        """
        self.assertEqual(IEnv.__abstractmethods__, _EXPECTED_ABSTRACTS)

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots so implementations stay dictionary free.

        Validates that implementations declaring ``__slots__`` do not
        inherit an unwanted instance dictionary from the contract.
        """
        self.assertEqual(IEnv.__dict__.get("__slots__"), ())

    def testCannotBeInstantiatedDirectly(self) -> None:
        """
        Reject direct instantiation of the contract.

        Validates that callers are forced to depend on a concrete facade
        implementation instead of the interface itself.
        """
        with self.assertRaises(TypeError):
            IEnv()

    def testRejectsPartialImplementations(self) -> None:
        """
        Reject subclasses that leave abstract methods unimplemented.

        Validates that a half-finished facade fails at construction time
        rather than at the first call site.
        """
        with self.assertRaises(TypeError):
            _IncompleteEnv()

    def testAcceptsCompleteImplementations(self) -> None:
        """
        Accept subclasses that implement the whole contract.

        Validates that the abstract surface is satisfiable without any
        additional hook or attribute.
        """
        self.assertEqual(_CompleteEnv.get("KEY", "default"), "default")
        self.assertTrue(_CompleteEnv.set("KEY", "value"))
        self.assertTrue(_CompleteEnv.unset("KEY"))
        self.assertEqual(_CompleteEnv.all(), {})
        self.assertTrue(_CompleteEnv.reload())

    def testMatchesTheParameterNamesOfTheImplementation(self) -> None:
        """
        Match the parameter names published by the shipped facade.

        Validates that ``Env`` can be substituted wherever the contract is
        expected without changing call sites.
        """
        for name in sorted(_EXPECTED_ABSTRACTS):
            expected = list(signature(getattr(IEnv, name)).parameters)
            actual = list(signature(getattr(Env, name)).parameters)
            self.assertEqual(actual, expected)

    def testIsImplementedByTheShippedFacade(self) -> None:
        """
        Recognise the shipped facade as a valid implementation.

        Validates that ``Env`` actually derives from the contract used
        across the framework.
        """
        self.assertTrue(issubclass(Env, IEnv))
        self.assertEqual(Env.__abstractmethods__, frozenset())
