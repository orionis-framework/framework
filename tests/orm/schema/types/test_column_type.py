from sqlalchemy.schema import CreateTable
from orionis.database.compiler import SQLCompiler
from orionis.database.exceptions import QueryException
from orionis.orm.schema import types as types_module
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import ColumnType, Enum, Integer, StrictArray
from orionis.test import TestCase

class TestColumnType(TestCase):
    """Verify logical column kinds are complete and reach SQL compilation."""

    def testEveryLogicalKindHasAConcreteDeclaration(self) -> None:
        """Match the exported declarations to the complete logical type catalog.

        Returns
        -------
        None
            Verify constructor coverage and compiler handling for every kind.
        """
        seen: set[ColumnType] = set()
        unsupported = {
            ColumnType.ARRAY,
            ColumnType.MATCH_TYPE,
            ColumnType.NUMERIC_COMMON,
            ColumnType.SCHEMA_TYPE,
        }
        for name in types_module.__all__:
            constructor = getattr(types_module, name)
            if constructor is ColumnType:
                continue
            if constructor is Enum:
                column = Enum("draft", "published")
            elif constructor is StrictArray:
                column = StrictArray(Integer())
            else:
                column = constructor()
            seen.add(column.column_type)
            definition = TableDefinition("type_probe", columns={"value": column})
            compiler = SQLCompiler()
            if column.column_type in unsupported:
                with self.assertRaises(QueryException):
                    compiler.compileCreateTable(definition)
            else:
                statement = compiler.compileCreateTable(definition)
                self.assertIsInstance(statement, CreateTable)
                self.assertEqual(statement.element.c.value.name, "value")
        self.assertEqual(seen, set(ColumnType))
