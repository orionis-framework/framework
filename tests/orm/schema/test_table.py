from dataclasses import FrozenInstanceError
from orionis.orm.schema.constraints import (
    CompositeForeignKey,
    TableIndex,
    UniqueConstraint,
)
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Integer, String
from orionis.test import TestCase

class TestTableDefinition(TestCase):
    """Verify table lookup and the metadata shared with the SQL compiler."""

    def testColumnLookupPreservesDefinitionOrder(self) -> None:
        """Look up declared columns without sorting or changing their names.

        Returns
        -------
        None
            Verify column order, membership, and missing-column behavior.
        """
        columns = {"name": String(), "id": Integer()}
        table = TableDefinition("accounts", columns)
        self.assertEqual(table.columnNames(), ("name", "id"))
        self.assertTrue(table.hasColumn("name"))
        self.assertFalse(table.hasColumn("missing"))
        self.assertIs(table.columns, columns)

    def testSchemalessTablesHaveIndependentColumnMappings(self) -> None:
        """Keep empty raw-table definitions independent from each other.

        Returns
        -------
        None
            Verify the default factory does not share mutable column state.
        """
        first = TableDefinition("first")
        second = TableDefinition("second")
        first.columns["id"] = Integer()
        self.assertEqual(second.columnNames(), ())
        self.assertEqual(second.primary_key, "id")
        self.assertEqual(second.foreign_keys, ())

    def testPreservesCompositeAndSchemaMetadata(self) -> None:
        """Retain the schema and complete composite constraint definitions.

        Returns
        -------
        None
            Verify compiler metadata is preserved in an immutable table object.
        """
        foreign = CompositeForeignKey(("account_id",), "accounts", ("id",))
        unique = UniqueConstraint(("tenant_id", "email"))
        index = TableIndex(("email",))
        table = TableDefinition(
            "members",
            schema="tenant",
            comment="Tenant members",
            primary_key="account_id",
            composite_primary_key=("tenant_id", "id"),
            unique_constraints=(unique,),
            foreign_keys=(foreign,),
            indexes=(index,),
        )
        self.assertEqual(table.schema, "tenant")
        self.assertEqual(table.comment, "Tenant members")
        self.assertEqual(table.composite_primary_key, ("tenant_id", "id"))
        self.assertIs(table.foreign_keys[0], foreign)
        self.assertIs(table.unique_constraints[0], unique)
        self.assertIs(table.indexes[0], index)
        self.assertFalse(hasattr(table, "__dict__"))
        attribute = "name"
        with self.assertRaises(FrozenInstanceError):
            setattr(table, attribute, "changed")
