from dataclasses import FrozenInstanceError, asdict
from orionis.orm.schema.constraints.composite_foreign_key import CompositeForeignKey
from orionis.test import TestCase

class TestCompositeForeignKey(TestCase):
    """Verify composite-key column correspondence and immutable metadata."""

    def testPreservesOrderedColumnsAndReferenceMetadata(self) -> None:
        """Keep local and referenced columns in their declared order.

        Returns
        -------
        None
            Verify every field consumed by the database compiler.
        """
        constraint = CompositeForeignKey(
            ("tenant_id", "account_id"),
            "accounts",
            ("tenant_id", "id"),
            name="fk_account",
        )
        self.assertEqual(
            asdict(constraint),
            {
                "columns": ("tenant_id", "account_id"),
                "ref_table": "accounts",
                "ref_columns": ("tenant_id", "id"),
                "name": "fk_account",
            },
        )
        self.assertFalse(hasattr(constraint, "__dict__"))
        attribute = "name"
        with self.assertRaises(FrozenInstanceError):
            setattr(constraint, attribute, "changed")

    def testConstraintNamesRemainOptional(self) -> None:
        """Leave naming to the engine when no name is supplied.

        Returns
        -------
        None
            Verify unnamed constraints retain their column correspondence.
        """
        constraint = CompositeForeignKey(("account_id",), "accounts", ("id",))
        self.assertIsNone(constraint.name)
        self.assertEqual(constraint.ref_columns, ("id",))
