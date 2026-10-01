import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from app.models.user import User
from database.schemas.model_has_roles_v1 import MODEL_HAS_ROLES_V1
from database.schemas.permissions_v1 import PERMISSIONS_V1
from database.schemas.role_has_permissions_v1 import ROLE_HAS_PERMISSIONS_V1
from database.schemas.roles_v1 import ROLES_V1
from database.schemas.users_v1 import USERS_V1
from database.seeders import s0000000001_create_admin_authorization as admin_seeder
from orionis.auth.authorization.registrar import PermissionRegistrar
from orionis.database.connection import Connection
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import QueryException
from orionis.database.migrations.context import migration_connection_scope
from orionis.database.seeders.runner import SeederRunner
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver

class TestAdminSeeder(unittest.IsolatedAsyncioTestCase):
    """Exercise the real user model and authorization tables together."""

    async def asyncSetUp(self) -> None:
        """
        Create isolated SQLite tables and pin the existing application APIs.

        Returns
        -------
        None
            Test dependencies are ready to use.
        """
        self.connection = Connection("admin_seeder", {
            "driver": "sqlite",
            "database": ":memory:",
            "foreign_key_constraints": True,
        })
        self.addAsyncCleanup(self.connection.disconnect)
        for definition in (
            USERS_V1,
            PERMISSIONS_V1,
            ROLES_V1,
            MODEL_HAS_ROLES_V1,
            ROLE_HAS_PERMISSIONS_V1,
        ):
            await self.connection.createTable(definition)

        manager = Mock(spec=IConnectionManager)
        manager.connection.return_value = self.connection
        self.manager = manager
        self.enterContext(patch.object(ConnectionResolver, "_manager", manager))
        self.registrar = PermissionRegistrar(QueryBuilder(manager))
        self.hasher = Argon2Hasher(memory=8, threads=1, time=1)
        self.hashMake = AsyncMock(side_effect=self.hasher.make)
        self.enterContext(patch.object(
            admin_seeder,
            "Hash",
            SimpleNamespace(make=self.hashMake),
        ))

    async def _run(self) -> None:
        """
        Run the seeder under the transaction supplied by its runner.

        Returns
        -------
        None
            Changes commit together or roll back together.
        """
        with migration_connection_scope(self.connection):
            async with self.connection.transaction():
                await admin_seeder.CreateAdminAuthorizationSeeder(
                    self.registrar,
                ).run()

    async def testCreatesHashedAdminAndBothAuthorizationAssociations(
        self,
    ) -> None:
        """Persist the user, role, permission, and exact pivot links.

        Returns
        -------
        None
            Verify the admin password is hashed and associations are exact.
        """
        await self._run()

        users = await self.connection.select(
            "SELECT id, name, email, password FROM users",
        )
        self.assertEqual(len(users), 1)
        user = users[0]
        self.assertEqual(user["name"], "Orionis Admin")
        self.assertEqual(user["email"], "admin@example.com")
        self.hashMake.assert_awaited_once_with("Orionis123*+")
        self.assertNotEqual(user["password"], "Orionis123*+")
        self.assertTrue(
            await self.hasher.check("Orionis123*+", user["password"]),
        )

        roles = await self.connection.select("SELECT id, name FROM roles")
        permissions = await self.connection.select(
            "SELECT id, name FROM permissions",
        )
        self.assertEqual([row["name"] for row in roles], ["admin"])
        self.assertEqual(
            [row["name"] for row in permissions], ["full_access"],
        )
        self.assertEqual(await self.connection.select(
            "SELECT permission_id, role_id FROM role_has_permissions",
        ), [{
            "permission_id": permissions[0]["id"],
            "role_id": roles[0]["id"],
        }])
        self.assertEqual(await self.connection.select(
            "SELECT role_id, model_type, model_id FROM model_has_roles",
        ), [{
            "role_id": roles[0]["id"],
            "model_type": "app.models.user.User",
            "model_id": str(user["id"]),
        }])

    async def testHashingFailureLeavesEveryTableEmpty(self) -> None:
        """Roll back authorization records if password hashing fails.

        Returns
        -------
        None
            Verify the failed transaction leaves every table empty.
        """
        self.hashMake.side_effect = RuntimeError("hash failed")
        with self.assertRaisesRegex(RuntimeError, "hash failed"):
            await self._run()

        for table in (
            "users", "roles", "permissions", "model_has_roles",
            "role_has_permissions",
        ):
            with self.subTest(table=table):
                rows = await self.connection.select(
                    f"SELECT * FROM {table}",  # noqa: S608
                )
                self.assertEqual(rows, [])

    async def testExistingEmailDoesNotGainAdministratorRole(self) -> None:
        """Roll back grants when the email belongs to an existing user.

        Returns
        -------
        None
            Verify the existing user remains unchanged and gains no role.
        """
        with migration_connection_scope(self.connection):
            existing = await User.create({
                "name": "Existing",
                "email": "admin@example.com",
                "password": "existing digest",
            })

        with self.assertRaises(QueryException):
            await self._run()

        self.assertEqual(await self.connection.select("SELECT * FROM roles"), [])
        self.assertEqual(
            await self.connection.select("SELECT * FROM permissions"), [],
        )
        self.assertEqual(
            await self.connection.select("SELECT * FROM model_has_roles"), [],
        )
        persisted = await User.find(existing.id)
        self.assertEqual(persisted.password, "existing digest")

    async def testRunnerDiscoversAndTracksBundledAdminSeeder(self) -> None:
        """Run the real admin seeder once through filesystem discovery.

        Returns
        -------
        None
            Verify discovery, tracking, and idempotent execution.
        """
        app = SimpleNamespace(
            basePath=Path.cwd(),
            path=lambda _key: Path.cwd() / "database" / "seeders",
            build=AsyncMock(side_effect=lambda cls: cls(self.registrar)),
        )
        runner = SeederRunner(app, self.manager)
        name = "s0000000001_create_admin_authorization"

        self.assertEqual(await runner.seed(), [name])
        self.assertEqual(await runner.seed(), [])
        app.build.assert_awaited_once_with(
            admin_seeder.CreateAdminAuthorizationSeeder,
        )
        rows = await self.connection.select(
            "SELECT seeder, batch, seeded_at FROM seeders",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["seeder"], name)
        self.assertEqual(rows[0]["batch"], 1)
        self.assertGreater(rows[0]["seeded_at"], 0)
        self.assertEqual(len(await self.connection.select("SELECT id FROM users")), 1)
