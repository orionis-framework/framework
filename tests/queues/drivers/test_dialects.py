from sqlalchemy.dialects import mssql, mysql, oracle, postgresql, sqlite
from orionis.database.compiler import SQLCompiler
from orionis.orm.query.expressions import (
    OrderClause,
    SelectPlan,
    UpdatePlan,
    WhereClause,
)
from orionis.queues.drivers.database import eligible_clauses
from orionis.queues.schema import build_failed_jobs_table, build_jobs_table
from orionis.test import TestCase


class TestQueueDialectPlans(TestCase):
    """Compile portable schemas and compare-and-swap claims for every dialect."""

    __slots__ = ()

    async def testCompilePortableClaims(self) -> None:
        """Compile candidate and atomic claim plans through all database dialects.

        Returns
        -------
        None
            Assert bounded lookup and conditional update without lock syntax.
        """
        definition = build_jobs_table("jobs")
        compiler = SQLCompiler("q_")
        select = compiler.compileSelect(SelectPlan(
            table=definition,
            wheres=eligible_clauses("high", 10.25),
            orders=[OrderClause("available_at"), OrderClause("id")],
            limit_value=1,
        ))
        update = compiler.compileUpdate(UpdatePlan(
            table=definition,
            values={
                "attempts": 2, "reservation_token": "owner",
                "reserved_until": 100.25,
            },
            wheres=[
                WhereClause("id", value="id"),
                WhereClause("attempts", value=1),
                *eligible_clauses("high", 10.25),
            ],
        ))
        for dialect in (
            sqlite.dialect(), mysql.dialect(), postgresql.dialect(),
            oracle.dialect(), mssql.dialect(),
        ):
            selected = str(select.compile(dialect=dialect)).lower()
            claimed = str(update.compile(dialect=dialect)).lower()
            self.assertIn("q_jobs", selected)
            self.assertNotIn("for update", selected)
            self.assertIn("update q_jobs", claimed)
            self.assertIn("where q_jobs.id", claimed)
            self.assertIn("q_jobs.attempts =", claimed)
            self.assertIn("q_jobs.available_at <=", claimed)
            self.assertIn("q_jobs.reserved_until is null", claimed)
            self.assertIn("reservation_token", claimed)

    async def testCompilePortableSchemas(self) -> None:
        """Compile native binary payloads and fractional timestamps portably.

        Returns
        -------
        None
            Assert both schemas compile without ORM or dialect-specific DDL.
        """
        compiler = SQLCompiler("q_")
        for definition in (
            build_jobs_table("jobs"), build_failed_jobs_table("failed_jobs"),
        ):
            statement = compiler.compileCreateTable(definition)
            for dialect in (
                sqlite.dialect(), mysql.dialect(), postgresql.dialect(),
                oracle.dialect(), mssql.dialect(),
            ):
                compiled = str(statement.compile(dialect=dialect)).lower()
                self.assertIn(f"q_{definition.name}", compiled)
                self.assertIn("payload", compiled)
                self.assertIn("attempts", compiled)
