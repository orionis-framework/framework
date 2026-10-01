from dataclasses import FrozenInstanceError, fields
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types import ColumnType, Integer
from orionis.test import TestCase

class TestColumnOptions(TestCase):
    """Verify immutable options and their transfer to column definitions."""

    def testEveryOptionIsTransferredToTheColumnDefinition(self) -> None:
        """Transfer all configured options without discarding object references.

        Returns
        -------
        None
            Verify each declared option is visible on the resulting column.
        """
        item = Integer()
        marker = object()
        options = ColumnOptions(
            length=90,
            precision=12,
            scale=3,
            decimal_return_scale=4,
            as_decimal=False,
            enum_values=("active", "inactive"),
            enum_name="state",
            native_enum=False,
            validate_strings=True,
            create_constraint=True,
            constraint_name="constraint",
            timezone=True,
            collation="binary",
            as_uuid=False,
            native_uuid=False,
            item_type=item,
            dimensions=2,
            as_tuple=True,
            zero_indexes=True,
            none_as_null=True,
            native=False,
            second_precision=6,
            day_precision=3,
            protocol=4,
            pickler=marker,
            impl=marker,
        )
        column = ColumnDefinition(ColumnType.STRING, options)
        for field in fields(ColumnOptions):
            self.assertEqual(getattr(column, field.name), getattr(options, field.name))
        self.assertIs(column.item_type, item)
        self.assertIs(column.pickler, marker)

    def testDefaultsRemainImmutableAndDictionaryFree(self) -> None:
        """Keep defaults immutable and prevent dynamic option attributes.

        Returns
        -------
        None
            Verify default semantics and rejection of reassigned options.
        """
        options = ColumnOptions()
        self.assertIsNone(options.length)
        self.assertTrue(options.as_decimal)
        self.assertTrue(options.native_uuid)
        self.assertFalse(options.none_as_null)
        self.assertFalse(hasattr(options, "__dict__"))
        attribute = "length"
        with self.assertRaises(FrozenInstanceError):
            setattr(options, attribute, 12)
