from orionis.test import TestCase
from tests.orm.test_package import assert_package_exports

EXPECTED_EXPORTS = {
    "BigInteger": ("orionis.orm.schema.types", "BigInteger"),
    "Boolean": ("orionis.orm.schema.types", "Boolean"),
    "ColumnDefinition": ("orionis.orm.schema.column", "ColumnDefinition"),
    "ColumnOptions": ("orionis.orm.schema.column", "ColumnOptions"),
    "ColumnType": ("orionis.orm.schema.types", "ColumnType"),
    "CompositeForeignKey": ("orionis.orm.schema.constraints", "CompositeForeignKey"),
    "Date": ("orionis.orm.schema.types", "Date"),
    "DateTime": ("orionis.orm.schema.types", "DateTime"),
    "Double": ("orionis.orm.schema.types", "Double"),
    "Enum": ("orionis.orm.schema.types", "Enum"),
    "Float": ("orionis.orm.schema.types", "Float"),
    "ForeignReference": ("orionis.orm.schema.constraints", "ForeignReference"),
    "Integer": ("orionis.orm.schema.types", "Integer"),
    "Interval": ("orionis.orm.schema.types", "Interval"),
    "LargeBinary": ("orionis.orm.schema.types", "LargeBinary"),
    "MatchType": ("orionis.orm.schema.types", "MatchType"),
    "Numeric": ("orionis.orm.schema.types", "Numeric"),
    "NumericCommon": ("orionis.orm.schema.types", "NumericCommon"),
    "PickleType": ("orionis.orm.schema.types", "PickleType"),
    "SchemaType": ("orionis.orm.schema.types", "SchemaType"),
    "SmallInteger": ("orionis.orm.schema.types", "SmallInteger"),
    "StrictArray": ("orionis.orm.schema.types", "StrictArray"),
    "StrictBigInt": ("orionis.orm.schema.types", "StrictBigInt"),
    "StrictBinary": ("orionis.orm.schema.types", "StrictBinary"),
    "StrictBlob": ("orionis.orm.schema.types", "StrictBlob"),
    "StrictChar": ("orionis.orm.schema.types", "StrictChar"),
    "StrictClob": ("orionis.orm.schema.types", "StrictClob"),
    "StrictDecimal": ("orionis.orm.schema.types", "StrictDecimal"),
    "StrictDoublePrecision": ("orionis.orm.schema.types", "StrictDoublePrecision"),
    "StrictInt": ("orionis.orm.schema.types", "StrictInt"),
    "StrictJson": ("orionis.orm.schema.types", "StrictJson"),
    "StrictNChar": ("orionis.orm.schema.types", "StrictNChar"),
    "StrictNVarChar": ("orionis.orm.schema.types", "StrictNVarChar"),
    "StrictReal": ("orionis.orm.schema.types", "StrictReal"),
    "StrictSmallInt": ("orionis.orm.schema.types", "StrictSmallInt"),
    "StrictTimestamp": ("orionis.orm.schema.types", "StrictTimestamp"),
    "StrictVarBinary": ("orionis.orm.schema.types", "StrictVarBinary"),
    "StrictVarChar": ("orionis.orm.schema.types", "StrictVarChar"),
    "String": ("orionis.orm.schema.types", "String"),
    "TableDefinition": ("orionis.orm.schema.table", "TableDefinition"),
    "TableIndex": ("orionis.orm.schema.constraints", "TableIndex"),
    "Text": ("orionis.orm.schema.types", "Text"),
    "Time": ("orionis.orm.schema.types", "Time"),
    "Unicode": ("orionis.orm.schema.types", "Unicode"),
    "UnicodeText": ("orionis.orm.schema.types", "UnicodeText"),
    "UniqueConstraint": ("orionis.orm.schema.constraints", "UniqueConstraint"),
    "Uuid": ("orionis.orm.schema.types", "Uuid"),
}

class TestSchemaPackage(TestCase):
    """Verify the orionis.orm.schema public export surface."""

    def testPublicExportsResolveToTheirOwningModules(self) -> None:
        """Keep public exports aligned with their declared implementation origins.

        Returns
        -------
        None
            Verify exact exported names and identities without shadowing modules.
        """
        assert_package_exports(self, "orionis.orm.schema", EXPECTED_EXPORTS)
