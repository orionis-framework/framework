# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import inspect
from orionis.localization.contracts.loader import ITranslationLoader
from orionis.localization.loader import TranslationLoader
from orionis.test import TestCase

# Methods every translation loader must implement.
_ABSTRACT_METHODS: frozenset[str] = frozenset({"availableLocales", "load"})


class TestTranslationLoaderContract(TestCase):
    """Validate the loader interface and its implementation parity."""

    def testDeclaresTheExpectedAbstractSurface(self) -> None:
        """Declare exactly the documented abstract methods.

        Validates that implementers know the complete set of methods
        they must provide.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(ITranslationLoader.__abstractmethods__, _ABSTRACT_METHODS)

    def testDeclaresEmptySlots(self) -> None:
        """Declare empty slots on the interface.

        Validates that implementations declaring slots do not gain an
        instance dictionary through the contract.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(ITranslationLoader.__slots__, ())

    def testFrameworkImplementationDerivesFromTheContract(self) -> None:
        """Derive the shipped loader from the interface.

        Validates that the framework implementation is substitutable
        wherever the contract is required.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(TranslationLoader, ITranslationLoader))

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
                    getattr(ITranslationLoader, method),
                    eval_str=True,
                )
                actual = inspect.signature(
                    getattr(TranslationLoader, method),
                    eval_str=True,
                )
                self.assertEqual(
                    list(actual.parameters.values())[1:],
                    list(expected.parameters.values())[1:],
                )
                self.assertEqual(actual.return_annotation, expected.return_annotation)
