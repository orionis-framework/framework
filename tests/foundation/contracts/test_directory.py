from abc import ABC
from inspect import isabstract, signature
from orionis.foundation.contracts.directory import IDirectory
from orionis.foundation.core_paths import CORE_APP_PATHS
from orionis.test import TestCase

def _method_name(key: str) -> str:
    """Convert a configured snake_case key to a camelCase method name.

    Parameters
    ----------
    key : str
        Configured application path key.

    Returns
    -------
    str
        CamelCase directory accessor name.
    """
    head, *tail = key.split("_")
    return head + "".join(part.capitalize() for part in tail)

class TestIDirectoryContract(TestCase):
    """Test the application directory contract."""

    def testIsAnAbstractClass(self) -> None:
        """Verify that IDirectory is an abstract ABC."""
        self.assertTrue(issubclass(IDirectory, ABC))
        self.assertTrue(isabstract(IDirectory))
        with self.assertRaises(TypeError):
            IDirectory()  # type: ignore[abstract]

    def testDeclaresEveryCorePathAccessor(self) -> None:
        """Verify that the contract mirrors CORE_APP_PATHS exactly."""
        expected = {"root", *(_method_name(key) for key in CORE_APP_PATHS)}
        self.assertEqual(IDirectory.__abstractmethods__, expected)

    def testDeclaresEmptySlots(self) -> None:
        """Verify that the contract does not add instance attributes."""
        self.assertEqual(IDirectory.__slots__, ())

    def testAccessorSignaturesAcceptOnlySelf(self) -> None:
        """Verify that each accessor has the expected method signature."""
        for method_name in IDirectory.__abstractmethods__:
            self.assertEqual(
                list(signature(getattr(IDirectory, method_name)).parameters),
                ["self"],
            )
