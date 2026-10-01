from __future__ import annotations
from orionis.orm.schema.types import (
    ColumnType,
    Enum,
)
from orionis.test import TestCase
from tests.orm.schema.types.test_package import assert_column_options

class TestEnum(TestCase):
    def testEnumRequiresValues(self) -> None:
        """Require at least one non-empty enum value.

        Validates the enum value guard.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        column = Enum("draft", "published")
        self.assertEqual(column.enum_values, ("draft", "published"))
        self.assertIs(column.column_type, ColumnType.ENUM)
        with self.assertRaises(ValueError):
            Enum()

class TestEnumOptions(TestCase):
    """Verify Enum constructor metadata consumed by the compiler."""

    def testDefaultAndConfiguredDeclarationOptions(self) -> None:
        """Preserve the logical type and all supplied constructor options.

        Returns
        -------
        None
            Verify fresh declarations and independent configured metadata.
        """
        default = Enum("draft", "published")
        assert_column_options(
            self,
            default,
            ColumnType.ENUM,
            enum_values=("draft", "published"),
            native_enum=True,
            create_constraint=False,
        )
        configured = Enum(
            "queued",
            "ready",
            name="states",
            create_constraint=True,
            native_enum=False,
            length=20,
            validate_strings=True,
        )
        assert_column_options(
            self,
            configured,
            ColumnType.ENUM,
            enum_values=("queued", "ready"),
            enum_name="states",
            create_constraint=True,
            native_enum=False,
            length=20,
            validate_strings=True,
        )
        self.assertIsNot(configured, default)

    def testRejectsEmptyAndNonStringEnumValues(self) -> None:
        """Reject enum entries that cannot describe a non-empty string value.

        Returns
        -------
        None
            Verify validation applies to every supplied enum entry.
        """
        for values in (("",), ("valid", ""), ("valid", None), (7,)):
            with self.assertRaises(ValueError):
                Enum(*values)  # type: ignore[arg-type]
