from dataclasses import FrozenInstanceError, asdict
from orionis.orm.schema.constraints.table_index import TableIndex
from orionis.test import TestCase

class TestTableIndex(TestCase):
    """Verify index order, uniqueness, and immutable compiler metadata."""

    def testPreservesNamedUniqueIndexOptions(self) -> None:
        """Retain ordered columns and the explicit uniqueness flag.

        Returns
        -------
        None
            Verify the named index metadata cannot be changed afterward.
        """
        index = TableIndex(("tenant_id", "email"), name="idx_email", unique=True)
        self.assertEqual(
            asdict(index),
            {
                "columns": ("tenant_id", "email"),
                "name": "idx_email",
                "unique": True,
            },
        )
        self.assertFalse(hasattr(index, "__dict__"))
        attribute = "unique"
        with self.assertRaises(FrozenInstanceError):
            setattr(index, attribute, False)

    def testUnnamedIndexesAreNotUniqueByDefault(self) -> None:
        """Keep ordinary unnamed indexes distinct from unique constraints.

        Returns
        -------
        None
            Verify the default index options passed to the compiler.
        """
        index = TableIndex(("created_at",))
        self.assertIsNone(index.name)
        self.assertFalse(index.unique)
