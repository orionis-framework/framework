# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify ORM schema table index behavior."""

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
            No return value.
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
            No return value.
        """
        index = TableIndex(("created_at",))
        self.assertIsNone(index.name)
        self.assertFalse(index.unique)
