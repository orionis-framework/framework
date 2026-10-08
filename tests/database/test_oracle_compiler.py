"""Oracle compilation regressions reproduced against the native thin driver."""

from sqlalchemy.dialects import oracle, postgresql
from orionis.database.compiler import SQLCompiler
from orionis.orm.query.expressions import SelectPlan, WhereClause
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import Float, Integer, Text
from orionis.test import TestCase


class TestOracleCompiler(TestCase):
    def definition(self, value=None, *, incrementing=False) -> TableDefinition:
        """
        Build a table definition with explicit key generation.

        Parameters
        ----------
        value : ColumnDefinition, optional
            Column to name ``value``; default to nullable text when omitted.
        incrementing : bool, optional
            Enable automatic primary key generation; default to False.

        Returns
        -------
        TableDefinition
            The entries table with an integer key and the selected value column.
        """
        identity = Integer().primary()
        if incrementing:
            identity.autoIncrement()
        identity.name = "id"
        value = Text().nullable() if value is None else value
        value.name = "value"
        return TableDefinition(name="entries", columns={"id": identity, "value": value})

    def testDeclaredAutoIncrementUsesOracleIdentityOnlyWhenRequested(self) -> None:
        """
        Verify that Oracle emits identity columns only when requested.

        Returns
        -------
        None
            Assert DDL generation for automatic and client-managed primary keys.
        """
        for incrementing in (False, True):
            with self.subTest(incrementing=incrementing):
                ddl = str(
                    SQLCompiler(driver="oracle")
                    .compileCreateTable(
                        self.definition(incrementing=incrementing),
                    )
                    .compile(dialect=oracle.dialect()),
                )
                self.assertEqual("IDENTITY" in ddl.upper(), incrementing)

    def testFloatDecimalPrecisionCompilesOnOracleAndKeepsResultOptions(self) -> None:
        """
        Verify Oracle float precision and decimal conversion options.

        Returns
        -------
        None
            Assert Oracle binary precision, result options, and PostgreSQL DDL.
        """
        definition = self.definition(Float(25, asdecimal=True, decimal_return_scale=3))
        ddl = SQLCompiler(driver="oracle").compileCreateTable(definition)
        self.assertIn("FLOAT(83)", str(ddl.compile(dialect=oracle.dialect())))
        native = ddl.element.c.value.type.dialect_impl(oracle.dialect())
        self.assertTrue(native.asdecimal)
        self.assertEqual(native.decimal_return_scale, 3)
        self.assertIn(
            "FLOAT(25)",
            str(
                SQLCompiler(driver="pgsql")
                .compileCreateTable(
                    definition,
                )
                .compile(dialect=postgresql.dialect()),
            ),
        )

    def testLargeTextEqualityAndInequalityUseBoundClobComparisons(self) -> None:
        """
        Verify that large text predicates use bound CLOB comparisons.

        Returns
        -------
        None
            Assert LOB comparison SQL, hidden payloads, and CLOB-typed bindings.
        """
        value = "private-bound-probe-" * 600
        for operator in ("=", "!="):
            with self.subTest(operator=operator):
                statement = SQLCompiler(driver="oracle").compileSelect(
                    SelectPlan(
                        table=self.definition(),
                        wheres=[WhereClause("value", operator=operator, value=value)],
                    ),
                )
                compiled = statement.compile(dialect=oracle.dialect())
                self.assertIn("DBMS_LOB.COMPARE", str(compiled).upper())
                self.assertNotIn(value, str(compiled))
                self.assertIn(value, compiled.params.values())
                self.assertTrue(
                    any(
                        str(binding.type.compile(dialect=oracle.dialect())).upper()
                        == "CLOB"
                        for binding in compiled.binds.values()
                    ),
                )

    def testNullTextPredicatesPreserveOracleNullSemantics(self) -> None:
        """
        Verify that NULL text predicates use native Oracle null checks.

        Returns
        -------
        None
            Assert ``IS NULL`` and ``IS NOT NULL`` without LOB comparisons.
        """
        for operator, expected in (("=", "IS NULL"), ("!=", "IS NOT NULL")):
            with self.subTest(operator=operator):
                compiled = (
                    SQLCompiler(driver="oracle")
                    .compileSelect(
                        SelectPlan(
                            table=self.definition(),
                            wheres=[
                                WhereClause("value", operator=operator, value=None),
                            ],
                        ),
                    )
                    .compile(dialect=oracle.dialect())
                )
                self.assertIn(expected, str(compiled).upper())
                self.assertNotIn("DBMS_LOB.COMPARE", str(compiled).upper())
