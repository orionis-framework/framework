from __future__ import annotations
import tests.orm.test_events as feature_fixtures

class TestSoftDeletes(feature_fixtures._ModelFeatureTestCase):
    """Soft delete behavior on instances and on the query builder."""

    async def testDeleteStampsInsteadOfRemoving(self) -> None:
        """Stamp the delete column instead of removing the row.

        Validates the instance-level soft delete.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await feature_fixtures.Account.query().firstOrFail()
        self.assertTrue(await account.delete())
        self.assertTrue(account.trashed())
        self.assertEqual(await feature_fixtures.Account.withTrashed().count(), 2)

    async def testTrashedRowsAreExcludedByDefault(self) -> None:
        """Hide soft deleted rows from ordinary queries.

        Validates the implicit soft delete constraint.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await feature_fixtures.Account.query().firstOrFail()
        await account.delete()
        self.assertEqual(await feature_fixtures.Account.count(), 1)

    async def testOnlyTrashedReturnsDeletedRows(self) -> None:
        """Restrict a query to soft deleted rows.

        Validates ``onlyTrashed``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await feature_fixtures.Account.query().firstOrFail()
        await account.delete()
        trashed = await feature_fixtures.Account.onlyTrashed().get()
        self.assertEqual([model.id for model in trashed], [account.id])

    async def testRestoreBringsTheRowBack(self) -> None:
        """Clear the delete stamp of a soft deleted row.

        Validates the instance-level restore.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await feature_fixtures.Account.query().firstOrFail()
        await account.delete()
        self.assertTrue(await account.restore())
        self.assertFalse(account.trashed())
        self.assertEqual(await feature_fixtures.Account.count(), 2)

    async def testForceDeleteRemovesTheRow(self) -> None:
        """Delete a soft-deleting model permanently.

        Validates ``forceDelete``.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        account = await feature_fixtures.Account.query().firstOrFail()
        await account.forceDelete()
        self.assertEqual(await feature_fixtures.Account.withTrashed().count(), 1)

    async def testBuilderDeleteSoftDeletesEveryMatch(self) -> None:
        """Soft delete through a mass delete query.

        Validates that the builder honors soft deletes too.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        self.assertEqual(await feature_fixtures.Account.query().delete(), 2)
        self.assertEqual(await feature_fixtures.Account.count(), 0)
        self.assertEqual(await feature_fixtures.Account.withTrashed().count(), 2)

    async def testBuilderRestoreAndForceDelete(self) -> None:
        """Restore and permanently delete through the builder.

        Validates the mass variants of both operations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.seed()
        await feature_fixtures.Account.query().delete()
        self.assertEqual(await feature_fixtures.Account.query().restore(), 2)
        self.assertEqual(await feature_fixtures.Account.count(), 2)
        self.assertEqual(await feature_fixtures.Account.query().forceDelete(), 2)
        self.assertEqual(await feature_fixtures.Account.withTrashed().count(), 0)
