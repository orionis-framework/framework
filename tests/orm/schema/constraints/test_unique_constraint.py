from dataclasses import FrozenInstanceError
from orionis.orm.schema.constraints.unique_constraint import UniqueConstraint
from orionis.test import TestCase

class TestUniqueConstraint(TestCase):
    """Verify ordered unique-column metadata and optional constraint names."""

    def testPreservesColumnOrderAndOptionalNames(self) -> None:
        """Retain a named constraint and its unnamed equivalent.

        Returns
        -------
        None
            Verify ordered fields, equality, and immutable value semantics.
        """
        columns = ("tenant_id", "email")
        constraint = UniqueConstraint(columns, name="unique_email")
        self.assertEqual(constraint.columns, columns)
        self.assertEqual(constraint.name, "unique_email")
        self.assertIsNone(UniqueConstraint(columns).name)
        self.assertEqual(constraint, UniqueConstraint(columns, "unique_email"))
        self.assertFalse(hasattr(constraint, "__dict__"))
        attribute = "name"
        with self.assertRaises(FrozenInstanceError):
            setattr(constraint, attribute, "changed")
