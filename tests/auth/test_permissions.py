import asyncio
import importlib
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4
from orionis.auth.authorization.registrar import PermissionRegistrar
from orionis.auth.authorization.repository import DatabasePermissionRepository
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.exceptions import AuthException
from orionis.auth.tokens.repository import AccessTokenRepository
from orionis.database.connection_manager import ConnectionManager
from orionis.database.connection import Connection
from orionis.database.compiler import SQLCompiler
from orionis.database.exceptions import QueryException
from orionis.database.migrations.migrator import Migrator
from orionis.database.schema.schema import Schema
from orionis.orm.query_builder import QueryBuilder
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.constraints import UniqueConstraint
from orionis.orm.schema.table import TableDefinition
from orionis.orm.schema.types import BigInteger, String
from orionis.test import TestCase
from tests.auth import test_manager as auth_fixtures

_AUTH_MIGRATIONS = (
    ("m0000000006_create_permissions_table", "CreatePermissionsTable"),
    ("m0000000007_create_roles_table", "CreateRolesTable"),
    (
        "m0000000008_create_model_has_permissions_table",
        "CreateModelHasPermissionsTable",
    ),
    ("m0000000009_create_model_has_roles_table", "CreateModelHasRolesTable"),
    ("m0000000010_create_role_has_permissions_table", "CreateRoleHasPermissionsTable"),
    (
        "m0000000011_create_personal_access_tokens_table",
        "CreatePersonalAccessTokensTable",
    ),
)

class _StubApp:
    """Application stub exposing a file backed SQLite database."""

    __slots__ = ("_database",)

    def __init__(self, database: str) -> None:
        """Store the SQLite database the connection points at."""
        self._database = database

    def config(self, key: str | None = None) -> Any:  # noqa: ANN401, ARG002
        """Return the database configuration tree."""
        return {
            "default": "sqlite",
            "connections": {
                "sqlite": {
                    "driver": "sqlite",
                    "database": self._database,
                    "prefix": "",
                },
            },
        }

class _Identity:
    """Authorizable double addressed by a polymorphic pair."""

    __slots__ = ("identifier", "kind")

    def __init__(self, identifier: object, kind: str = "tests.Account") -> None:
        """Store the polymorphic type and the identifier."""
        self.identifier = identifier
        self.kind = kind

    def getAuthorizableType(self) -> str:
        """Return the polymorphic type of this identity."""
        return self.kind

    def getAuthorizableId(self) -> object:
        """Return the identifier of this identity."""
        return self.identifier

class _CountingConnection(Connection):
    """Count actual SELECT statements reaching the SQL connection."""

    __slots__ = ("selects",)

    def __init__(self, config: dict) -> None:
        """Start an isolated SQL connection with an empty read counter."""
        super().__init__("sqlite", config)
        self.selects = 0

    async def select(
        self, query: object, bindings: dict | None = None,
    ) -> list[dict]:
        """Count a statement before delegating to SQLAlchemy Core."""
        self.selects += 1
        return await super().select(query, bindings)

def named_table(name: str) -> TableDefinition:
    """Build a ``permissions`` or ``roles`` shaped table."""
    columns = {
        "id": BigInteger().primary().autoIncrement(),
        "name": String(255),
    }
    for column_name, column in columns.items():
        column.name = column_name
    return TableDefinition(
        name=name,
        columns=columns,
        primary_key="id",
        unique_constraints=(
            UniqueConstraint(columns=("name",)),
        ),
    )

def morph_table(name: str, owner: str) -> TableDefinition:
    """Build a polymorphic pivot table keyed by owner and model."""
    columns = {
        owner: BigInteger(),
        "model_type": String(255),
        "model_id": String(255),
    }
    for column_name, column in columns.items():
        column.name = column_name
    return TableDefinition(
        name=name,
        columns=columns,
        composite_primary_key=(owner, "model_id", "model_type"),
    )

def role_permissions_table() -> TableDefinition:
    """Build the pivot table linking roles with permissions."""
    columns = {
        "permission_id": BigInteger(),
        "role_id": BigInteger(),
    }
    for column_name, column in columns.items():
        column.name = column_name
    return TableDefinition(
        name="role_has_permissions",
        columns=columns,
        composite_primary_key=("permission_id", "role_id"),
    )

class _AuthorizationCase(TestCase):
    """Base case creating the authorization schema on SQLite."""

    async def asyncSetUp(self) -> None:
        """Create every authorization table on a temporary database."""
        self._tmp = tempfile.TemporaryDirectory()
        database = str(Path(self._tmp.name) / "auth.sqlite")

        self.app = _StubApp(database)
        self.manager = ConnectionManager(self.app)
        self._previous_manager = ConnectionResolver._manager
        ConnectionResolver.setManager(self.manager)
        self.connection = self.manager.connection("sqlite")

        await self.connection.createTable(named_table("permissions"))
        await self.connection.createTable(named_table("roles"))
        await self.connection.createTable(
            morph_table("model_has_permissions", "permission_id"),
        )
        await self.connection.createTable(
            morph_table("model_has_roles", "role_id"),
        )
        await self.connection.createTable(role_permissions_table())

        self.db = QueryBuilder(self.manager)
        self.registrar = PermissionRegistrar(self.db)
        self.repository = DatabasePermissionRepository(self.db)

    async def asyncTearDown(self) -> None:
        """Release the connection and remove the temporary database."""
        ConnectionResolver.setManager(self._previous_manager)
        await self.connection.disconnect()
        self._tmp.cleanup()

class TestPermissionRegistrar(_AuthorizationCase):
    """Validate how permissions and roles are created and attached."""

    async def testCreatesAPermissionOnce(self) -> None:
        """Validates that creation is idempotent.

        Seeders run repeatedly, so a second call must reuse the row.
        """
        first = await self.registrar.createPermission("users.view")
        second = await self.registrar.createPermission("users.view")

        self.assertEqual(first, second)
        rows = await self.db.table("permissions").get()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "users.view")

    async def testCreatesARoleOnce(self) -> None:
        """Validates that role creation is idempotent too.

        Roles are stored in a table with the same unique constraint.
        """
        first = await self.registrar.createRole("admin")
        second = await self.registrar.createRole("admin")

        self.assertEqual(first, second)
        self.assertEqual(len(await self.db.table("roles").get()), 1)

    async def testAttachingAPermissionTwiceIsIdempotent(self) -> None:
        """Validates that the composite key absorbs duplicates.

        Granting the same permission twice must not fail.
        """
        identity = _Identity(1)
        await self.registrar.givePermissionTo(identity, "users.view")
        await self.registrar.givePermissionTo(identity, "users.view")

        rows = await self.db.table("model_has_permissions").get()
        self.assertEqual(len(rows), 1)

    async def testRevokesADirectPermission(self) -> None:
        """Validates that a granted permission can be taken back.

        Only the pivot row is removed, never the permission itself.
        """
        identity = _Identity(1)
        await self.registrar.givePermissionTo(identity, "users.view")
        await self.registrar.revokePermissionFrom(identity, "users.view")

        self.assertEqual(len(await self.db.table("model_has_permissions").get()), 0)
        self.assertEqual(len(await self.db.table("permissions").get()), 1)

    async def testRevokingAnUnknownPermissionIsSafe(self) -> None:
        """Validates the no-op path of a revocation.

        Removing something that was never granted is not an error.
        """
        await self.registrar.revokePermissionFrom(_Identity(1), "ghost")

    async def testAssignsAndRemovesRoles(self) -> None:
        """Validates the role attachment lifecycle.

        Roles use the very same polymorphic pivot shape.
        """
        identity = _Identity(1)
        await self.registrar.assignRole(identity, "admin", "editor")
        self.assertEqual(len(await self.db.table("model_has_roles").get()), 2)

        await self.registrar.removeRole(identity, "editor")
        rows = await self.db.table("model_has_roles").get()
        self.assertEqual(len(rows), 1)

    async def testGrantsAndRevokesPermissionsOnARole(self) -> None:
        """Validates the role to permission pivot.

        This is what makes a role a grouping of permissions.
        """
        await self.registrar.grantToRole("admin", "users.view", "users.delete")
        self.assertEqual(
            len(await self.db.table("role_has_permissions").get()), 2,
        )

        await self.registrar.revokeFromRole("admin", "users.delete")
        self.assertEqual(
            len(await self.db.table("role_has_permissions").get()), 1,
        )

    async def testRevokingFromAnUnknownRoleIsSafe(self) -> None:
        """Validates the no-op path when the role does not exist.

        A missing role cannot hold any permission.
        """
        await self.registrar.revokeFromRole("ghost", "users.view")

    async def testConcurrentCreationsConvergeOnASingleRow(self) -> None:
        """Validates that creation is race free.

        The unique key decides the winner instead of a read-then-write.
        """
        results = await asyncio.gather(
            *(self.registrar.createPermission("users.view") for _ in range(6)),
        )

        self.assertEqual(len(set(results)), 1)
        self.assertEqual(len(await self.db.table("permissions").get()), 1)

    async def testUnexpectedInsertFailuresAreNeverReportedAsSuccess(self) -> None:
        """Propagate broken pivot storage instead of swallowing every SQL error."""
        await self.connection.dropTable("model_has_permissions")
        with self.assertRaises(QueryException):
            await self.registrar.givePermissionTo(_Identity(1), "users.view")

    async def testDuplicateAttachmentsPreserveTheOuterTransaction(self) -> None:
        """Keep duplicate recovery local to its own savepoint."""
        identity = _Identity(1)
        await self.registrar.givePermissionTo(identity, "users.view")
        with self.assertRaises(ValueError):
            async with self.db.transaction():
                await self.db.table("roles").insert({"name": "rolled-back"})
                await self.registrar.givePermissionTo(identity, "users.view")
                error_msg = "abort the outer transaction"
                raise ValueError(error_msg)
        self.assertEqual(await self.db.table("roles").count(), 0)
        self.assertEqual(await self.db.table("model_has_permissions").count(), 1)

    async def testRejectsInvalidAuthorizationNames(self) -> None:
        """Reject names that would be ambiguous or exceed the schema."""
        for name in ("", " users.view", "roles." * 50):
            with self.assertRaises(AuthException):
                await self.registrar.createPermission(name)

    async def testGrantsWorkWithAColdSchemaCache(self) -> None:
        """Resolve generated IDs when the process did not execute the migrations."""
        self.connection._compiler = SQLCompiler()
        identity = _Identity(1)
        await self.registrar.assignRole(identity, "editor")
        await self.registrar.grantToRole("editor", "posts.update")
        permissions, roles = await self.repository.loadFor(identity)
        self.assertEqual(permissions, frozenset({"posts.update"}))
        self.assertEqual(roles, frozenset({"editor"}))

class TestDatabasePermissionRepository(_AuthorizationCase):
    """Validate how the effective authorization is resolved."""

    async def testAnIdentityWithoutAnythingResolvesEmpty(self) -> None:
        """Validates the baseline for a brand new identity.

        Authorization defaults to deny.
        """
        permissions, roles = await self.repository.loadFor(_Identity(1))
        self.assertEqual(permissions, frozenset())
        self.assertEqual(roles, frozenset())

    async def testResolvesDirectPermissions(self) -> None:
        """Validates permissions attached straight to the identity.

        Direct permissions do not require any role.
        """
        identity = _Identity(1)
        await self.registrar.givePermissionTo(
            identity, "users.view", "users.create",
        )

        permissions, roles = await self.repository.loadFor(identity)

        self.assertEqual(permissions, frozenset({"users.view", "users.create"}))
        self.assertEqual(roles, frozenset())

    async def testResolvesPermissionsInheritedFromARole(self) -> None:
        """Validates that a role hands its permissions to its holders.

        This is the whole point of grouping permissions in roles.
        """
        identity = _Identity(1)
        await self.registrar.grantToRole("admin", "users.view", "users.delete")
        await self.registrar.assignRole(identity, "admin")

        permissions, roles = await self.repository.loadFor(identity)

        self.assertEqual(permissions, frozenset({"users.view", "users.delete"}))
        self.assertEqual(roles, frozenset({"admin"}))

    async def testMergesSeveralRolesAndDirectPermissions(self) -> None:
        """Validates that both sources are combined.

        An identity may hold many roles plus its own permissions.
        """
        identity = _Identity(1)
        await self.registrar.grantToRole("admin", "users.view")
        await self.registrar.grantToRole("editor", "posts.update")
        await self.registrar.assignRole(identity, "admin", "editor")
        await self.registrar.givePermissionTo(identity, "billing.read")

        permissions, roles = await self.repository.loadFor(identity)

        self.assertEqual(
            permissions,
            frozenset({"users.view", "posts.update", "billing.read"}),
        )
        self.assertEqual(roles, frozenset({"admin", "editor"}))

    async def testDeduplicatesOverlappingSources(self) -> None:
        """Validates that a permission granted twice appears once.

        Direct and inherited grants must not multiply.
        """
        identity = _Identity(1)
        await self.registrar.grantToRole("admin", "users.view")
        await self.registrar.assignRole(identity, "admin")
        await self.registrar.givePermissionTo(identity, "users.view")

        permissions, _ = await self.repository.loadFor(identity)

        self.assertEqual(permissions, frozenset({"users.view"}))

    async def testNeverLeaksAuthorizationBetweenIdentities(self) -> None:
        """Validates the polymorphic filtering of the pivot tables.

        Two identities of the same type must stay independent.
        """
        first = _Identity(1)
        second = _Identity(2)
        await self.registrar.givePermissionTo(first, "users.view")

        permissions, _ = await self.repository.loadFor(second)

        self.assertEqual(permissions, frozenset())

    async def testNeverLeaksAuthorizationBetweenTypes(self) -> None:
        """Validates that the ``model_type`` column is honoured.

        Two different models may share an identifier value.
        """
        account = _Identity(1, "tests.Account")
        team = _Identity(1, "tests.Team")
        await self.registrar.givePermissionTo(account, "users.view")

        permissions, _ = await self.repository.loadFor(team)

        self.assertEqual(permissions, frozenset())

    async def testDirectOnlyIdentitiesHaveNoRoles(self) -> None:
        """Resolve direct grants without inventing a role for their owner."""
        identity = _Identity(1)
        await self.registrar.givePermissionTo(identity, "users.view")

        permissions, roles = await self.repository.loadFor(identity)

        self.assertEqual(roles, frozenset())
        self.assertEqual(permissions, frozenset({"users.view"}))

    async def testUuidIdentitiesOwnRolesAndDirectPermissions(self) -> None:
        """Store UUID owner keys without coupling RBAC to integer models."""
        identity = _Identity(uuid4())
        await self.registrar.assignRole(identity, "editor")
        await self.registrar.grantToRole("editor", "posts.update")
        await self.registrar.givePermissionTo(identity, "posts.view")
        permissions, roles = await self.repository.loadFor(identity)
        self.assertEqual(permissions, frozenset({"posts.update", "posts.view"}))
        self.assertEqual(roles, frozenset({"editor"}))

    async def testAnIdentityWithoutRbacSupportHasNoPermissions(self) -> None:
        """Keep authentication-only identities usable with resource policies."""
        self.assertEqual(
            await self.repository.loadFor(object()), (frozenset(), frozenset()),
        )

class TestAuthMigrations(TestCase):
    """Run the shipped authorization and token migrations on an isolated database."""

    async def asyncSetUp(self) -> None:
        """Bind migration schema access to a temporary database, never the app DB."""
        self._tmp = tempfile.TemporaryDirectory()
        self.app = auth_fixtures._StubApp(str(Path(self._tmp.name) / "schema.sqlite"))
        self.app._tree["database"]["connections"]["sqlite"][
            "foreign_key_constraints"
        ] = True
        self.manager = ConnectionManager(self.app)
        self._previous_manager = ConnectionResolver._manager
        ConnectionResolver.setManager(self.manager)
        self.connection = self.manager.connection()
        self.db = QueryBuilder(self.manager)
        self.registrar = PermissionRegistrar(self.db)
        self.repository = DatabasePermissionRepository(self.db)
        self.tokens = AccessTokenRepository(self.app, self.db)
        self._modules: list[tuple[object, object]] = []
        migrations: dict[str, type] = {}
        for module_name, class_name in _AUTH_MIGRATIONS:
            module = importlib.import_module(f"database.migrations.{module_name}")
            self._modules.append((module, module.Schema))
            module.Schema = Schema(self.manager)
            migrations[module_name] = getattr(module, class_name)
        self.migrator = Migrator(self.app, self.manager)
        self.migrator._Migrator__discovered_cache = migrations

    async def asyncTearDown(self) -> None:
        """Restore migration globals and the original database resolver."""
        for module, schema in self._modules:
            module.Schema = schema
        ConnectionResolver.setManager(self._previous_manager)
        await self.manager.disconnect()
        self._tmp.cleanup()

    async def testRealMigrationsSupportUuidOwnersAndRollback(self) -> None:
        """Apply real DDL, issue grants and tokens, then roll back all six tables."""
        applied = await self.migrator.migrate()
        self.assertEqual(len(applied), 6)
        self.assertEqual(await self.migrator.migrate(), [])
        identity = _Identity(uuid4())
        await self.registrar.assignRole(identity, "editor")
        await self.registrar.grantToRole("editor", "posts.update")
        await self.registrar.givePermissionTo(identity, "posts.view")
        permissions, roles = await self.repository.loadFor(identity)
        self.assertEqual(permissions, frozenset({"posts.view", "posts.update"}))
        self.assertEqual(roles, frozenset({"editor"}))
        issued = await self.tokens.create(identity, "migration-check")
        self.assertIsNotNone(await self.tokens.findByPlainText(issued.plain_text))
        tables = await self.connection.select(
            "SELECT name FROM sqlite_master WHERE type = :kind", {"kind": "table"},
        )
        self.assertNotIn("users", {row["name"] for row in tables})
        self.assertEqual(await self.migrator.rollback(), list(reversed(applied)))

    async def testForeignKeysDoNotPermitOrphanedRoleGrants(self) -> None:
        """Keep role and permission deletion explicit while references exist."""
        await self.migrator.migrate()
        role_id = await self.registrar.createRole("editor")
        await self.registrar.assignRole(_Identity(1), "editor")
        with self.assertRaises(QueryException):
            await self.db.table("roles").where("id", role_id).delete()
        await self.registrar.removeRole(_Identity(1), "editor")
        self.assertEqual(await self.db.table("roles").where("id", role_id).delete(), 1)

class TestAuthorizationQueryBudget(_AuthorizationCase):
    """Measure the query budget for repeated and concurrent permission checks."""

    async def asyncSetUp(self) -> None:
        """Replace the temporary connection with a counting implementation."""
        await super().asyncSetUp()
        await self.connection.disconnect()
        self.connection = _CountingConnection(self.manager.configFor("sqlite"))
        self.manager._cached_connections["sqlite"] = self.connection

    async def testConcurrentSnapshotsIssueExactlyOneSelect(self) -> None:
        """Load roles and effective permissions in one statement per context."""
        identity = _Identity(1)
        await self.registrar.assignRole(identity, "editor")
        await self.registrar.grantToRole("editor", "posts.update")
        await self.registrar.givePermissionTo(identity, "posts.view")
        context = AuthenticationContext(identity=identity, repository=self.repository)
        self.connection.selects = 0
        snapshots = await asyncio.gather(*(
            context.authorization() for _ in range(12)
        ))
        self.assertEqual(self.connection.selects, 1)
        self.assertEqual(len({id(snapshot) for snapshot in snapshots}), 1)
        self.assertTrue(snapshots[0].can("posts.update"))
        self.assertTrue(snapshots[0].can("posts.view"))
        self.assertTrue(snapshots[0].hasRole("editor"))
