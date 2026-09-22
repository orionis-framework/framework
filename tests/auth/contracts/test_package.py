from orionis.auth import contracts
from orionis.test import TestCase


class TestContractsPackage(TestCase):
    """Validate the public surface of the contracts package."""

    def testEveryContractDeclaresEmptySlots(self) -> None:
        """Inspect the ``__slots__`` declared by each abstract base.

        Validates that no contract silently gives an instance dictionary
        to its implementations, which would defeat their own slots.
        """
        for name in contracts.__all__:
            contract = getattr(contracts, name)
            self.assertIn("__slots__", contract.__dict__, name)
            self.assertEqual(contract.__slots__, (), name)

    def testTheExportListStaysSortedAndResolvable(self) -> None:
        """Resolve every advertised contract through the package.

        Validates that the entry point stays usable and that its order
        keeps review diffs readable.
        """
        self.assertEqual(list(contracts.__all__), sorted(contracts.__all__))
        for name in contracts.__all__:
            self.assertTrue(hasattr(contracts, name), name)
