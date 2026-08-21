import inspect
from orionis.localization.contracts.translator import ITranslator
from orionis.localization.translator import Translator
from orionis.test import TestCase

# Methods every translator must implement.
_ABSTRACT_METHODS: frozenset[str] = frozenset({
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
})

def parameter_names(owner: type, method: str) -> list[str]:
    """
    Return the parameter names declared by *method* on *owner*.

    Parameters
    ----------
    owner : type
        Class owning the inspected method.
    method : str
        Name of the method to inspect.

    Returns
    -------
    list[str]
        Ordered parameter names of the method signature.
    """
    return list(inspect.signature(getattr(owner, method)).parameters)

class TestTranslatorContract(TestCase):
    """Validate the translator interface and its implementation parity."""

    def testDeclaresTheExpectedAbstractSurface(self) -> None:
        """
        Declare exactly the documented abstract methods.

        Validates that implementers know the complete set of methods
        they must provide.
        """
        self.assertEqual(ITranslator.__abstractmethods__, _ABSTRACT_METHODS)

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots on the interface.

        Validates that implementations declaring slots do not gain an
        instance dictionary through the contract.
        """
        self.assertEqual(ITranslator.__slots__, ())

    def testFrameworkImplementationDerivesFromTheContract(self) -> None:
        """
        Derive the shipped translator from the interface.

        Validates that the framework implementation is substitutable
        wherever the contract is required.
        """
        self.assertTrue(issubclass(Translator, ITranslator))

    def testImplementationMirrorsTheContractSignatures(self) -> None:
        """
        Mirror the contract signatures in the implementation.

        Validates that callers relying on the interface can invoke the
        implementation with the very same arguments.
        """
        for method in sorted(_ABSTRACT_METHODS):
            self.assertEqual(
                parameter_names(Translator, method),
                parameter_names(ITranslator, method),
                method,
            )

    def testFallbackFlagStaysKeywordOnly(self) -> None:
        """
        Keep the existence fallback flag keyword-only.

        Validates that boolean traps are avoided on both sides of the
        contract.
        """
        for owner in (ITranslator, Translator):
            parameter = inspect.signature(owner.has).parameters["fallback"]
            self.assertEqual(parameter.kind, inspect.Parameter.KEYWORD_ONLY)
