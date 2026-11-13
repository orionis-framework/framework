# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
import inspect
from orionis.localization.contracts.translator import ITranslator
from orionis.localization.translator import Translator
from orionis.test import TestCase

# Methods every translator must implement.
_ABSTRACT_METHODS: frozenset[str] = frozenset(
    {
        "availableLocales",
        "choice",
        "flush",
        "forget",
        "get",
        "getLocale",
        "has",
        "missing",
        "reload",
        "setLocale",
    },
)


class TestTranslatorContract(TestCase):
    """Validate the translator interface and its implementation parity."""

    def testDeclaresTheExpectedAbstractSurface(self) -> None:
        """Declare exactly the documented abstract methods.

        Validates that implementers know the complete set of methods
        they must provide.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(ITranslator.__abstractmethods__, _ABSTRACT_METHODS)

    def testDeclaresEmptySlots(self) -> None:
        """Declare empty slots on the interface.

        Validates that implementations declaring slots do not gain an
        instance dictionary through the contract.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(ITranslator.__slots__, ())

    def testFrameworkImplementationDerivesFromTheContract(self) -> None:
        """Derive the shipped translator from the interface.

        Validates that the framework implementation is substitutable
        wherever the contract is required.

        Returns
        -------
        None
            No return value.
        """
        self.assertTrue(issubclass(Translator, ITranslator))

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
                    getattr(ITranslator, method),
                    eval_str=True,
                )
                actual = inspect.signature(getattr(Translator, method), eval_str=True)
                self.assertEqual(
                    list(actual.parameters.values())[1:],
                    list(expected.parameters.values())[1:],
                )
                self.assertEqual(actual.return_annotation, expected.return_annotation)

    def testFallbackFlagStaysKeywordOnly(self) -> None:
        """Keep the existence fallback flag keyword-only.

        Validates that boolean traps are avoided on both sides of the
        contract.

        Returns
        -------
        None
            No return value.
        """
        for owner in (ITranslator, Translator):
            parameter = inspect.signature(owner.has).parameters["fallback"]
            self.assertEqual(parameter.kind, inspect.Parameter.KEYWORD_ONLY)
