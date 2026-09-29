from __future__ import annotations
from typing import TYPE_CHECKING, ClassVar
from unittest.mock import patch
from orionis.database.connection_manager import ConnectionManager
from orionis.orm import Integer, Model, String
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.table import TableDefinition
from orionis.support.facades.db import DB
from orionis.test import TestCase

if TYPE_CHECKING:
    from orionis.orm.relations import (
        BelongsToManyRelation,
        BelongsToRelation,
        HasManyRelation,
    )

class _StubApp:
    """Minimal application stub exposing the database configuration."""

    def config(self, key: str) -> dict:  # noqa: ARG002
        """Return the requested database configuration.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.

        Returns
        -------
        dict
            Value produced by the helper.
        """
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {
                    "driver": "sqlite",
                    "database": ":memory:",
                    "prefix": "",
                },
            },
        }

def _pivot_table(name: str, first: str, second: str) -> TableDefinition:
    """Build a bare pivot table with two integer columns.

    Parameters
    ----------
    name : str
        Value supplied for ``name``.
    first : str
        Value supplied for ``first``.
    second : str
        Value supplied for ``second``.

    Returns
    -------
    TableDefinition
        Value produced by the helper.
    """
    columns = {first: Integer(), second: Integer()}
    for key, column in columns.items():
        column.name = key
    return TableDefinition(name=name, columns=columns)

class Team(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False

    def players(self) -> HasManyRelation[Player]:
        """Every player on this team.

        Returns
        -------
        HasManyRelation[Player]
            Value produced by the helper.
        """
        return self.hasMany(Player)

    def members(self) -> BelongsToManyRelation[Member]:
        """Every member linked to this team through the pivot table.

        Returns
        -------
        BelongsToManyRelation[Member]
            Value produced by the helper.
        """
        return self.belongsToMany(Member)

class Player(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    team_id = Integer().nullable()
    timestamps = False

    fillable: ClassVar[list[str]] = ["name", "team_id"]

    def team(self) -> BelongsToRelation[Team]:
        """Return the team owning this player.

        Returns
        -------
        BelongsToRelation[Team]
            Value produced by the helper.
        """
        return self.belongsTo(Team)

class Member(Model):
    id = Integer().primary().autoIncrement()
    name = String()
    timestamps = False

    def teams(self) -> BelongsToManyRelation[Team]:
        """Every team this member is linked to through the pivot table.

        Returns
        -------
        BelongsToManyRelation[Team]
            Value produced by the helper.
        """
        return self.belongsToMany(Team)

class TestRelationsWithTransactions(TestCase):
    """
    Integration tests validating relations compose with real transactions.

    Every relationship terminal ultimately delegates to the same
    :class:`~orionis.database.connection.Connection` a plain model query
    would use, so it must honor the same task-local transaction/rollback
    semantics documented for the rest of the ORM.
    """

    async def asyncSetUp(self) -> None:
        """Wire an isolated in-memory manager and create every table.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._manager = ConnectionManager(_StubApp())
        ConnectionResolver.setManager(self._manager)
        facade = patch.object(DB, "_pinned_instance", QueryBuilder(self._manager))
        facade.start()
        self.addCleanup(facade.stop)
        self._connection = self._manager.connection()
        await self._connection.createTable(Team.__meta__.table)
        await self._connection.createTable(Player.__meta__.table)
        await self._connection.createTable(Member.__meta__.table)
        await self._connection.createTable(
            _pivot_table("member_team", "member_id", "team_id"),
        )

    async def asyncTearDown(self) -> None:
        """Dispose the manager and clear the resolver after each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        await self._manager.disconnect()
        ConnectionResolver.clear()

    async def testHasManyCreateRollsBackWithTransaction(self) -> None:
        """Roll back a related row created inside a failed transaction.

        Validates that ``HasManyRelation.create()`` participates in the
        surrounding transaction like any other write.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        RuntimeError
            Raised by this helper to exercise the failure path.
        """
        team = await Team.create({"name": "Reds"})

        with self.assertRaises(RuntimeError):
            async with self._connection.transaction():
                await team.players().create({"name": "Ana"})
                error_msg = "force rollback"
                raise RuntimeError(error_msg)

        players = await team.players().get()
        self.assertEqual(len(players), 0)

    async def testHasManyCreateCommitsWithTransaction(self) -> None:
        """Persist a related row created inside a successful transaction.

        Validates the happy path alongside the rollback test above.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        team = await Team.create({"name": "Blues"})

        async with self._connection.transaction():
            await team.players().create({"name": "Bob"})

        players = await team.players().get()
        self.assertEqual([p.name for p in players], ["Bob"])

    async def testBelongsToManyAttachRollsBackWithTransaction(self) -> None:
        """Roll back pivot rows inserted through ``attach()`` on failure.

        Validates that pivot-table mutations honor the same transaction
        boundaries as any other write.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        RuntimeError
            Raised by this helper to exercise the failure path.
        """
        member = await Member.create({"name": "Ana"})
        team = await Team.create({"name": "Reds"})

        with self.assertRaises(RuntimeError):
            async with self._connection.transaction():
                await member.teams().attach(team.id)
                error_msg = "force rollback"
                raise RuntimeError(error_msg)

        teams = await member.teams().get()
        self.assertEqual(len(teams), 0)

    async def testBelongsToManyAttachCommitsWithTransaction(self) -> None:
        """Persist pivot rows inserted through ``attach()`` on success.

        Validates the happy path alongside the rollback test above.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        member = await Member.create({"name": "Bob"})
        team = await Team.create({"name": "Blues"})

        async with self._connection.transaction():
            await member.teams().attach(team.id)

        teams = await member.teams().get()
        self.assertEqual([t.name for t in teams], ["Blues"])

    async def testNestedTransactionSavepointRollsBackRelationWrite(self) -> None:
        """Roll back only the inner savepoint, keeping the outer commit.

        Validates relations compose with nested transactions the same
        way plain model writes already do.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        RuntimeError
            Raised by this helper to exercise the failure path.
        """
        team = await Team.create({"name": "Reds"})

        async with self._connection.transaction():
            await team.players().create({"name": "Kept"})
            with self.assertRaises(RuntimeError):
                async with self._connection.transaction():
                    await team.players().create({"name": "Discarded"})
                    error_msg = "force savepoint rollback"
                    raise RuntimeError(error_msg)

        players = await team.players().get()
        self.assertEqual([p.name for p in players], ["Kept"])

class TestRelationsWithDbTable(TestCase):
    """
    Integration tests validating relations compose with ``DB.table()``.

    ``BelongsToManyRelation`` resolves its pivot rows through the same
    :class:`~orionis.orm.query.raw_builder.RawQueryBuilder` that backs
    ``DB.table()``; these tests cross-check both entry points agree on
    the same physical rows.
    """

    async def asyncSetUp(self) -> None:
        """Wire an isolated in-memory manager and create every table.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._manager = ConnectionManager(_StubApp())
        ConnectionResolver.setManager(self._manager)
        connection = self._manager.connection()
        facade = patch.object(DB, "_pinned_instance", QueryBuilder(self._manager))
        facade.start()
        self.addCleanup(facade.stop)
        await connection.createTable(Team.__meta__.table)
        await connection.createTable(Player.__meta__.table)
        await connection.createTable(Member.__meta__.table)
        await connection.createTable(
            _pivot_table("member_team", "member_id", "team_id"),
        )

    async def asyncTearDown(self) -> None:
        """Dispose the manager and clear the resolver after each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        await self._manager.disconnect()
        ConnectionResolver.clear()

    async def testAttachIsVisibleThroughDbTable(self) -> None:
        """Read pivot rows inserted by ``attach()`` directly with ``DB.table()``.

        Validates that the pivot table used by the relationship is a
        regular table indistinguishable from any other raw query target.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        member = await Member.create({"name": "Ana"})
        team = await Team.create({"name": "Reds"})

        await member.teams().attach(team.id)

        rows = await DB.table("member_team").get()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["member_id"], member.id)
        self.assertEqual(rows[0]["team_id"], team.id)

    async def testDbTableInsertIsVisibleThroughRelation(self) -> None:
        """Read a pivot row inserted directly with ``DB.table()``.

        Validates the inverse direction: the relationship is just a
        query, not a separate storage mechanism.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        member = await Member.create({"name": "Bob"})
        team = await Team.create({"name": "Blues"})

        await DB.table("member_team").insert(
            {"member_id": member.id, "team_id": team.id},
        )

        teams = await member.teams().get()
        self.assertEqual([t.name for t in teams], ["Blues"])

    async def testDetachRemovesRowVisibleToDbTable(self) -> None:
        """Confirm ``detach()`` also removes the row from ``DB.table()``.

        Validates both entry points observe the same underlying table.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        member = await Member.create({"name": "Ana"})
        team = await Team.create({"name": "Reds"})
        await member.teams().attach(team.id)

        await member.teams().detach(team.id)

        rows = await DB.table("member_team").get()
        self.assertEqual(len(rows), 0)

    async def testBelongsToJoinsAgreeWithDbTableJoin(self) -> None:
        """Cross-check ``belongsTo`` against a manual ``DB.table()`` join.

        Validates the relationship's inferred foreign key matches what a
        hand-written join over the physical tables would use.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        team = await Team.create({"name": "Reds"})
        await Player.create({"name": "Ana", "team_id": team.id})

        player = await Player.query().first()
        owner = await player.team()

        joined = await (
            DB.table("players")
            .join("teams", "players.team_id", "=", "teams.id")
            .where("players.id", player.id)
            .select("teams.name")
            .first()
        )
        self.assertIsNotNone(owner)
        self.assertEqual(owner.name, joined["name"])
