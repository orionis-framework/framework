from orionis.auth import concerns
from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.concerns.functions import model_primary_key
from orionis.test import TestCase


class TestConcernsPackage(TestCase):
    """Validate the public surface of the concerns package."""

    def testExportsTheMixinsAndTheirHelper(self) -> None:
        """Resolve every advertised name through the package.

        Validates the entry point applications import their identity
        mixins from.
        """
        self.assertIs(concerns.Authenticatable, Authenticatable)
        self.assertIs(concerns.Authorizable, Authorizable)
        self.assertIs(concerns.model_primary_key, model_primary_key)

    def testTheExportListStaysSorted(self) -> None:
        """Compare the export list against its sorted counterpart.

        Validates that the package keeps a deterministic order.
        """
        self.assertEqual(list(concerns.__all__), sorted(concerns.__all__))
