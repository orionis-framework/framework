# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import inspect
from orionis.localization.contracts.manager import ILocalizationManager
from orionis.localization.manager import LocalizationManager
from orionis.test import TestCase

# Methods every localization manager must implement.
_ABSTRACT_METHODS: frozenset[str] = frozenset({"translator"})


class TestLocalizationManagerContract(TestCase):
    """Validate the manager interface and its implementation parity."""

    def testDeclaresTheExpectedAbstractSurface(self) -> None:
        """Declare exactly the documented abstract methods.

        Validates that the manager exposes a single entry point to the
        shared translator.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(
            ILocalizationManager.__abstractmethods__,
            _ABSTRACT_METHODS,
        )

    def testDeclaresEmptySlots(self) -> None:
        """Declare empty slots on the interface.

        Validates that implementations declaring slots do not gain an
        instance dictionary through the contract.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(ILocalizationManager.__slots__, ())

    def testFrameworkImplementationDerivesFromTheContract(self) -> None:
        """Derive the shipped manager from the interface.

        Validates that the container can resolve the manager through
        its contract.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(
            issubclass(LocalizationManager, ILocalizationManager),
        )

    def testImplementationMirrorsTheContractSignatures(self) -> None:
        """Mirror the contract signatures in the implementation.

        Validates that callers relying on the interface can invoke the
        implementation with the very same arguments.

        Returns
        -------
        None
            No return value.
        """
        for method in sorted(_ABSTRACT_METHODS):
            with self.subTest(method=method):
                expected = inspect.signature(
                    getattr(ILocalizationManager, method),
                    eval_str=True,
                )
                actual = inspect.signature(
                    getattr(LocalizationManager, method),
                    eval_str=True,
                )
                self.assertEqual(
                    list(actual.parameters.values())[1:],
                    list(expected.parameters.values())[1:],
                )
                self.assertEqual(actual.return_annotation, expected.return_annotation)
