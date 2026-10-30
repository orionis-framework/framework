import asyncio
from typing import TYPE_CHECKING, Any, Self
from unittest.mock import patch
from orionis.auth.guards.token_guard import TokenGuard
from orionis.auth.identity.provider import ModelIdentityProvider
from orionis.database.connection import Connection
from tests.auth.test_identity_and_session import Account, accounts_table, build_app
from tests.auth.test_tokens import _TokenCase, bearer_request

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult
    from sqlalchemy.ext.asyncio import AsyncConnection
    from sqlalchemy.sql.base import Executable
    from orionis.database.threaded.connection import ThreadedConnection
    from orionis.database.threaded.result import ThreadedResult

class TestCombinedTokenLookup(_TokenCase):
    """Keep late revocation checks while reducing native lookup round trips."""

    async def asyncSetUp(self: Self) -> None:
        """
        Create an isolated native model provider and token repository.

        Returns
        -------
        None
            Complete the operation without returning a value.
        """
        await super().asyncSetUp()
        await self.connection.createTable(accounts_table())
        await self.db.table("accounts").insert(
            {
                "id": 1,
                "email": "one@example.test",
                "password": "unused",
                "active": True,
            },
        )
        self.owner = await Account.query().find(1)
        self.provider = ModelIdentityProvider(build_app(), None)
        self.guard = TokenGuard(self.repository, self.provider)

    async def testTwoStatementsAndNoIdentityCache(self: Self) -> None:
        """
        Use one joined SELECT and one final validity UPDATE.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        issued = await self.repository.create(self.owner, "test", abilities=["read"])
        statements = []
        original = Connection._run

        async def counted(
            connection: Connection,
            raw: AsyncConnection | ThreadedConnection,
            statement: Executable,
            *args: object,
            **kwargs: object,
        ) -> CursorResult[Any] | ThreadedResult:
            """
            Record each statement before delegating to the native connection.

            Parameters
            ----------
            connection : Connection
                Orionis connection whose native execution is intercepted.
            raw : AsyncConnection | ThreadedConnection
                Open native connection used to execute the statement.
            statement : Executable
                SQLAlchemy statement to record or execute.
            *args : object
                Positional arguments forwarded to the wrapped operation.
            **kwargs : object
                Keyword arguments forwarded to the wrapped operation.

            Returns
            -------
            CursorResult[Any] | ThreadedResult
                Result returned by the original connection execution.
            """
            statements.append(str(statement))
            return await original(connection, raw, statement, *args, **kwargs)

        with patch.object(Connection, "_run", counted):
            result = await self.guard.resolve(bearer_request(issued.plain_text))
        self.assertIsNotNone(result)
        self.assertEqual(len(statements), 2)
        self.assertIn("JOIN", statements[0])
        self.assertIn("UPDATE", statements[1])
        self.assertEqual(result.abilities, frozenset({"read"}))
        await self.repository.revoke(issued.access_token.id)
        self.assertIsNone(await self.guard.resolve(bearer_request(issued.plain_text)))

    async def testJoinedLookupUsesOwnerPrimaryKeyIndex(self: Self) -> None:
        """
        Cast the token key while preserving indexed owner lookup.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        issued = await self.repository.create(self.owner, "test")
        statements = []
        original = Connection._run

        async def capture(
            connection: Connection,
            raw: AsyncConnection | ThreadedConnection,
            statement: Executable,
            *args: object,
            **kwargs: object,
        ) -> CursorResult[Any] | ThreadedResult:
            """
            Capture the statement used by the joined token lookup.

            Parameters
            ----------
            connection : Connection
                Orionis connection whose native execution is intercepted.
            raw : AsyncConnection | ThreadedConnection
                Open native connection used to execute the statement.
            statement : Executable
                SQLAlchemy statement to record or execute.
            *args : object
                Positional arguments forwarded to the wrapped operation.
            **kwargs : object
                Keyword arguments forwarded to the wrapped operation.

            Returns
            -------
            CursorResult[Any] | ThreadedResult
                Native execution result or the empty result double used for compilation.
            """
            statements.append(statement)
            return await original(connection, raw, statement, *args, **kwargs)

        with patch.object(Connection, "_run", capture):
            await self.guard.resolve(bearer_request(issued.plain_text))
        sql = str(statements[0].compile(compile_kwargs={"literal_binds": True}))
        plan = await self.connection.select("EXPLAIN QUERY PLAN " + sql)
        details = " ".join(row["detail"] for row in plan)
        self.assertIn("SEARCH accounts USING INTEGER PRIMARY KEY", details)

    async def testRevocationAfterHydrationStillRejectsAuthentication(
        self: Self,
    ) -> None:
        """
        Reject tokens revoked while identity events are running.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        issued = await self.repository.create(self.owner, "test")
        entered, released = asyncio.Event(), asyncio.Event()
        from orionis.orm.query.builder import ModelQueryBuilder

        original = ModelQueryBuilder._fireRetrieved

        async def pause(query: ModelQueryBuilder, models: list[Account]) -> None:
            """
            Pause model hydration events until the revocation check can run.

            Parameters
            ----------
            query : ModelQueryBuilder
                Model query builder dispatching retrieval events.
            models : list[Account]
                Hydrated account models whose events are paused.

            Returns
            -------
            None
                Complete the operation without returning a value.
            """
            entered.set()
            await released.wait()
            await original(query, models)

        with patch.object(ModelQueryBuilder, "_fireRetrieved", pause):
            resolving = asyncio.create_task(
                self.guard.resolve(bearer_request(issued.plain_text)),
            )
            try:
                await asyncio.wait_for(entered.wait(), 5)
                await self.repository.revoke(issued.access_token.id)
            finally:
                released.set()
            self.assertIsNone(await resolving)

    async def testMalformedOwnerKeysAreRejectedWithoutDatabaseCastErrors(
        self: Self,
    ) -> None:
        """
        Bound SQL casts before evaluating malformed stored identifiers.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        issued = await self.repository.create(self.owner, "test")
        for value in ("bad", "1--2", "9223372036854775808", "-9223372036854775809", ""):
            await (
                self.db.table("personal_access_tokens")
                .where("id", issued.access_token.id)
                .update({"tokenable_id": value})
            )
            self.assertIsNone(
                await self.guard.resolve(bearer_request(issued.plain_text)),
            )

    async def testIntegerBoundariesAndGlobalScope(self: Self) -> None:
        """
        Accept valid signed keys and honor the model's scoped identity filters.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        for identifier in (-9223372036854775808, 0, 9223372036854775807):
            await self.db.table("accounts").insert(
                {
                    "id": identifier,
                    "email": "boundary@example.test",
                    "password": "unused",
                    "active": True,
                },
            )
            owner = await Account.query().find(identifier)
            issued = await self.repository.create(owner, "boundary")
            result = await self.guard.resolve(bearer_request(issued.plain_text))
            self.assertEqual(result.identity.id, identifier)
        issued = await self.repository.create(self.owner, "scoped")
        await self.db.table("accounts").where("id", 1).update({"active": False})
        with patch.dict(
            Account.__meta__.global_scopes,
            {
                "active_only": lambda query: query.where("active", True),
            },
        ):
            self.assertIsNone(
                await self.guard.resolve(bearer_request(issued.plain_text)),
            )

    async def testJoinedStatementsCompileForSupportedSqlDialects(self: Self) -> None:
        """
        Preserve dialect-specific limit, quoting, string length and guarded casts.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        from types import SimpleNamespace

        from sqlalchemy.dialects import mssql, mysql, oracle, postgresql, sqlite

        from orionis.auth.tokens.lookup import lookup_owner

        statements = []

        async def capture(
            _connection: Connection,
            _raw: AsyncConnection | ThreadedConnection,
            statement: Executable,
            *_args: object,
            **_kwargs: object,
        ) -> SimpleNamespace:
            """
            Capture the statement used by the joined token lookup.

            Parameters
            ----------
            _connection : Connection
                Orionis connection replaced by the test double.
            _raw : AsyncConnection | ThreadedConnection
                Native connection replaced by the test double.
            statement : Executable
                SQLAlchemy statement to record or execute.
            *_args : object
                Unused positional arguments accepted by the test double.
            **_kwargs : object
                Unused keyword arguments accepted by the test double.

            Returns
            -------
            SimpleNamespace
                Native execution result or the empty result double used for compilation.
            """
            statements.append(statement)
            return SimpleNamespace(mappings=list)

        for name, dialect in (
            ("sqlite", sqlite.dialect()),
            ("pgsql", postgresql.dialect()),
            ("mysql", mysql.dialect()),
            ("oracle", oracle.dialect()),
            ("sqlserver", mssql.dialect()),
        ):
            with (
                patch.dict(self.connection._config, driver=name),
                patch.object(Connection, "_run", capture),
            ):
                result = await lookup_owner(
                    self.db.table("personal_access_tokens").where("token", "digest"),
                    self.provider,
                    self.repository._fromRow,
                )
            self.assertIsNone(result)
            sql = str(statements[-1].compile(dialect=dialect)).lower()
            self.assertIn("cast(case", sql)
            if name == "sqlserver":
                self.assertIn("len(", sql)
                self.assertNotIn("length(", sql)
