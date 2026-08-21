import orionis.schemas
from orionis.schemas.schema import Schema
from orionis.test import TestCase

class TestSchemasPackage(TestCase):

    def testPackageExportsTheSchemaBaseClass(self) -> None:
        """
        Re-export the schema base class at package level.

        Validates that ``orionis.schemas.Schema`` is the declaration base
        class and not the validator utility sharing its name.
        """
        self.assertIs(orionis.schemas.Schema, Schema)

    def testPublicApiIsLimitedToSchema(self) -> None:
        """
        Advertise only the schema base class as public API.

        Validates that the package does not leak internal helpers.
        """
        self.assertEqual(orionis.schemas.__all__, ["Schema"])
