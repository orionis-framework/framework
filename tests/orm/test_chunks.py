# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from typing import Self
from orionis.orm.exceptions import InvalidQueryException
from tests.auth.test_identity_and_session import Account, accounts_table
from tests.auth.test_tokens import _TokenCase


class TestChunkedQueries(_TokenCase):
    """Use real SQLite queries to check bounded hydration and paging semantics."""

    async def asyncSetUp(self: Self) -> None:
        """Create isolated rows for real bounded queries.

        Returns
        -------
        None
            No return value.
        """
        await super().asyncSetUp()
        await self.connection.createTable(accounts_table())
        await self.db.table("accounts").insert(
            [
                {
                    "id": i,
                    "email": f"{i}@example.test",
                    "password": "unused",
                    "active": True,
                }
                for i in range(1, 24)
            ],
        )

    async def testLimitsOffsetsAndModels(self: Self) -> None:
        """Apply original bounds without modifying the builder.

        Returns
        -------
        None
            No return value.
        """
        query = Account.query().orderBy("id").offset(3).limit(13)
        batches = [batch async for batch in query.chunks(5)]
        self.assertEqual([len(batch) for batch in batches], [5, 5, 3])
        self.assertEqual(
            [model.id for batch in batches for model in batch],
            list(range(4, 17)),
        )
        self.assertEqual(query.toPlan().offset_value, 3)
        self.assertEqual(query.toPlan().limit_value, 13)
        self.assertEqual(len(await query.get()), 13)

    async def testEarlyExitReleasesConnectionAndInvalidOrder(self: Self) -> None:
        """Close iterators without retaining cursors or transactions.

        Returns
        -------
        None
            No return value.
        """
        query = self.db.table("accounts").orderBy("id")
        batches = query.chunks(4)
        self.assertEqual(len(await anext(batches)), 4)
        await batches.aclose()
        self.assertFalse(self.connection.inTransaction())
        self.assertEqual(await self.db.table("accounts").count(), 23)
        with self.assertRaises(InvalidQueryException):
            await anext(self.db.table("accounts").chunks())
        with self.assertRaises(ValueError):
            await anext(query.chunks(0))
