import inspect
from orionis.localization.contracts.manager import ILocalizationManager
from orionis.localization.manager import LocalizationManager
from orionis.test import TestCase

# Methods every localization manager must implement.
_ABSTRACT_METHODS: frozenset[str] = frozenset({"translator"})

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

class TestLocalizationManagerContract(TestCase):
    """Validate the manager interface and its implementation parity."""

    def testDeclaresTheExpectedAbstractSurface(self) -> None:
        """
        Declare exactly the documented abstract methods.

        Validates that the manager exposes a single entry point to the
        shared translator.
        """
        self.assertEqual(
            ILocalizationManager.__abstractmethods__,
            _ABSTRACT_METHODS,
        )

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots on the interface.

        Validates that implementations declaring slots do not gain an
        instance dictionary through the contract.
        """
        self.assertEqual(ILocalizationManager.__slots__, ())

    def testFrameworkImplementationDerivesFromTheContract(self) -> None:
        """
        Derive the shipped manager from the interface.

        Validates that the container can resolve the manager through
        its contract.
        """
        self.assertTrue(
            issubclass(LocalizationManager, ILocalizationManager),
        )

    def testImplementationMirrorsTheContractSignatures(self) -> None:
        """
        Mirror the contract signatures in the implementation.

        Validates that callers relying on the interface can invoke the
        implementation with the very same arguments.
        """
        for method in sorted(_ABSTRACT_METHODS):
            self.assertEqual(
                parameter_names(LocalizationManager, method),
                parameter_names(ILocalizationManager, method),
                method,
            )
