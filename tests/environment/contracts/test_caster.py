# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from abc import ABC
from inspect import isabstract, signature
from orionis.environment.contracts.caster import IEnvironmentCaster
from orionis.environment.dynamic.caster import EnvironmentCaster
from orionis.environment.enums.value_type import EnvironmentValueType
from orionis.test import TestCase

# Abstract surface the contract is expected to publish.
_EXPECTED_ABSTRACTS: frozenset[str] = frozenset({"get", "to"})

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class _CompleteCaster(IEnvironmentCaster):
    """Minimal implementation covering the whole contract."""

    __slots__ = ()

    def get(self) -> object:
        """Return a canned value.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return "value"

    def to(self, type_hint: str | EnvironmentValueType) -> str:
        """Return a canned serialised representation.

        Parameters
        ----------
        type_hint : str | EnvironmentValueType
            Value supplied for ``type_hint``.

        Returns
        -------
        str
            Value produced by the helper.
        """
        hint = (
            type_hint.value
            if isinstance(type_hint, EnvironmentValueType)
            else type_hint
        )
        return f"{hint}:value"


class _IncompleteCaster(IEnvironmentCaster):
    """Implementation that deliberately leaves ``to`` unimplemented."""

    __slots__ = ()

    def get(self) -> object:
        """Return a canned value.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return "value"


# ---------------------------------------------------------------------------
# TestEnvironmentCasterContract
# ---------------------------------------------------------------------------


class TestEnvironmentCasterContract(TestCase):
    def testIsAnAbstractBaseClass(self) -> None:
        """Expose the caster contract as an abstract base class.

        Validates that the contract cannot be used as a concrete service
        and participates in the ABC registration machinery.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(IEnvironmentCaster, ABC))
        self.assertTrue(isabstract(IEnvironmentCaster))

    def testPublishesExactlyTheDocumentedAbstractSurface(self) -> None:
        """Publish exactly the documented abstract method surface.

        Validates that no method is silently added to or removed from the
        contract without updating its implementations.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(
            IEnvironmentCaster.__abstractmethods__,
            _EXPECTED_ABSTRACTS,
        )

    def testDeclaresEmptySlots(self) -> None:
        """Declare empty slots so implementations stay dictionary free.

        Validates that concrete casters declaring ``__slots__`` do not
        inherit an unwanted instance dictionary from the contract.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(IEnvironmentCaster.__dict__.get("__slots__"), ())

    def testCannotBeInstantiatedDirectly(self) -> None:
        """Reject direct instantiation of the contract.

        Validates that callers are forced to depend on a concrete caster
        implementation instead of the interface itself.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            IEnvironmentCaster()

    def testRejectsPartialImplementations(self) -> None:
        """Reject subclasses that leave an abstract method unimplemented.

        Validates that a half-finished caster fails at construction time
        rather than at the first call site.

        Returns
        -------
        None
            No return value.
        """
        with self.assertRaises(TypeError):
            _IncompleteCaster()

    def testAcceptsCompleteImplementations(self) -> None:
        """Accept subclasses that implement the whole contract.

        Validates that the abstract surface is satisfiable without any
        additional hook or attribute.

        Returns
        -------
        None
            No return value.
        """
        caster = _CompleteCaster()
        self.assertEqual(caster.get(), "value")
        self.assertEqual(caster.to("int"), "int:value")

    def testMatchesTheSignaturesOfTheImplementation(self) -> None:
        """Match the resolved signatures published by the shipped caster.

        Validates that ``EnvironmentCaster`` can be substituted wherever
        the contract is expected without changing call sites.

        Returns
        -------
        None
            No return value.
        """
        for name in sorted(_EXPECTED_ABSTRACTS):
            with self.subTest(method=name):
                expected = signature(getattr(IEnvironmentCaster, name), eval_str=True)
                actual = signature(getattr(EnvironmentCaster, name), eval_str=True)
                self.assertEqual(actual, expected)

    def testIsImplementedByTheShippedCaster(self) -> None:
        """Recognise the shipped caster as a valid implementation.

        Validates that the concrete class actually derives from the
        contract used across the framework.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(EnvironmentCaster, IEnvironmentCaster))
