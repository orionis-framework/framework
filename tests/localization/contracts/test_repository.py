import inspect
from orionis.localization.contracts.repository import ITranslationRepository
from orionis.localization.repository import TranslationRepository
from orionis.test import TestCase

# Methods every translation repository must implement.
_ABSTRACT_METHODS: frozenset[str] = frozenset({
    "flush",
    "forget",
    "get",
    "has",
    "loadedLocales",
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

class TestTranslationRepositoryContract(TestCase):
    """Validate the repository interface and its implementation parity."""

    def testDeclaresTheExpectedAbstractSurface(self) -> None:
        """
        Declare exactly the documented abstract methods.

        Validates that implementers know the complete set of methods
        they must provide.
        """
        self.assertEqual(
            ITranslationRepository.__abstractmethods__,
            _ABSTRACT_METHODS,
        )

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots on the interface.

        Validates that implementations declaring slots do not gain an
        instance dictionary through the contract.
        """
        self.assertEqual(ITranslationRepository.__slots__, ())

    def testFrameworkImplementationDerivesFromTheContract(self) -> None:
        """
        Derive the shipped repository from the interface.

        Validates that the framework implementation is substitutable
        wherever the contract is required.
        """
        self.assertTrue(
            issubclass(TranslationRepository, ITranslationRepository),
        )

    def testImplementationMirrorsTheContractSignatures(self) -> None:
        """
        Mirror the contract signatures in the implementation.

        Validates that callers relying on the interface can invoke the
        implementation with the very same arguments.
        """
        for method in sorted(_ABSTRACT_METHODS):
            self.assertEqual(
                parameter_names(TranslationRepository, method),
                parameter_names(ITranslationRepository, method),
                method,
            )
