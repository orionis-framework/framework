from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime
from importlib import import_module
from unittest.mock import Mock, patch

from app.models.user import User
from database.schemas.users_v1 import USERS_V1
from orionis.database.connection import Connection
from orionis.database.contracts.connection_manager import IConnectionManager
from orionis.database.exceptions import QueryException
from orionis.database.migrations.context import migration_connection_scope
from orionis.database.schema.schema import Schema
from orionis.orm.exceptions import MassAssignmentException
from orionis.orm.resolver import ConnectionResolver
from orionis.orm.schema.types import String
from orionis.support.facades.schema import Schema as SchemaFacade


_TABLE_COLUMNS = {
    "scheduler_tasks": ("id", "next_run_time", "job_state"),
    "cache": ("cache_key", "cache_value", "expiration"),
    "cache_locks": ("cache_key", "owner", "expiration"),
    "sessions": ("id", "payload", "expires_at"),
    "users": (
        "id", "name", "email", "email_verified_at", "password",
        "remember_token", "active", "created_at", "updated_at",
    ),
    "permissions": ("id", "name", "created_at", "updated_at"),
    "roles": ("id", "name", "created_at", "updated_at"),
    "model_has_permissions": ("permission_id", "model_type", "model_id"),
    "model_has_roles": ("role_id", "model_type", "model_id"),
    "role_has_permissions": ("permission_id", "role_id"),
    "personal_access_tokens": (
        "id", "tokenable_type", "tokenable_id", "name", "token", "abilities",
        "last_used_at", "expires_at", "revoked_at", "created_at", "updated_at",
    ),
    "password_reset_tokens": (
        "email", "token", "user_id", "password_fingerprint", "created_at",
    ),
}


class TestApplicationSchemas(unittest.IsolatedAsyncioTestCase):
    """Exercise application migrations against a private physical database."""

    async def asyncSetUp(self) -> None:
        """Bind the real migrations and model to an isolated SQLite connection."""
        self.connection = Connection("application_schemas", {
            "driver": "sqlite",
            "database": ":memory:",
            "foreign_key_constraints": True,
        })
        self.addAsyncCleanup(self.connection.disconnect)
        self.manager = Mock(spec=IConnectionManager)
        self.manager.connection.return_value = self.connection
        self.enterContext(patch.object(
            ConnectionResolver, "_manager", self.manager,
        ))
        self.enterContext(patch.object(
            SchemaFacade, "_pinned_instance", Schema(self.manager),
        ))
        self.migrations = []
        for number, table in enumerate(_TABLE_COLUMNS, 1):
            module = import_module(
                f"database.migrations.m{number:010d}_create_{table}_table",
            )
            class_name = (
                "Create" + "".join(part.title() for part in table.split("_"))
                + "Table"
            )
            self.migrations.append(getattr(module, class_name)())
        await self._migrateUp()

    async def _migrateUp(self) -> None:
        """Apply every application migration using its connection context."""
        with migration_connection_scope(self.connection):
            for migration in self.migrations:
                await migration.up()

    async def _tableNames(self) -> set[str]:
        """Read application table names from the SQLite catalog."""
        rows = await self.connection.select(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'",
        )
        return {row["name"] for row in rows}

    async def testMigrationsRollbackAndReplay(self) -> None:
        """Create, remove, and recreate the complete application schema."""
        self.assertEqual(await self._tableNames(), set(_TABLE_COLUMNS))
        self.assertEqual(
            await self.connection.select("PRAGMA foreign_keys"),
            [{"foreign_keys": 1}],
        )
        with migration_connection_scope(self.connection):
            for migration in reversed(self.migrations):
                await migration.down()
        self.assertEqual(await self._tableNames(), set())
        await self._migrateUp()
        self.assertEqual(await self._tableNames(), set(_TABLE_COLUMNS))
        self.manager.connection.assert_not_called()

    async def testPhysicalColumnsAndPrimaryKeysPreserveTheOriginalSchema(
        self,
    ) -> None:
        """Keep column order, storage types, nullability, and primary keys."""
        primary_keys = {
            "cache": ("cache_key",),
            "cache_locks": ("cache_key",),
            "model_has_permissions": (
                "permission_id", "model_id", "model_type",
            ),
            "model_has_roles": ("role_id", "model_id", "model_type"),
            "role_has_permissions": ("permission_id", "role_id"),
            "password_reset_tokens": ("email",),
        }
        for table, names in _TABLE_COLUMNS.items():
            with self.subTest(table=table):
                columns = await self.connection.select(
                    f'PRAGMA table_info("{table}")',
                )
                self.assertEqual(tuple(row["name"] for row in columns), names)
                actual_key = tuple(
                    row["name"] for row in sorted(
                        columns, key=lambda row: row["pk"],
                    ) if row["pk"]
                )
                self.assertEqual(
                    actual_key, primary_keys.get(table, ("id",)),
                )
        user_columns = {
            row["name"]: row
            for row in await self.connection.select("PRAGMA table_info(users)")
        }
        self.assertEqual(user_columns["id"]["type"], "INTEGER")
        self.assertEqual(user_columns["name"]["type"], "VARCHAR(255)")
        self.assertEqual(user_columns["remember_token"]["type"], "VARCHAR(100)")
        self.assertEqual(user_columns["active"]["type"], "BOOLEAN")
        nullable = {
            name for name, row in user_columns.items() if not row["notnull"]
        }
        self.assertEqual(nullable, {
            "email_verified_at", "remember_token", "created_at", "updated_at",
        })

    async def testIndexesCoverStorageAndAuthorizationLookups(self) -> None:
        """Retain actual indexes used for expiration and authorization queries."""
        expected = {
            "scheduler_tasks": {(False, ("next_run_time",))},
            "users": {(True, ("email",))},
            "permissions": {(True, ("name",))},
            "roles": {(True, ("name",))},
            "model_has_permissions": {(False, ("model_id", "model_type"))},
            "model_has_roles": {(False, ("model_id", "model_type"))},
            "role_has_permissions": {(False, ("role_id", "permission_id"))},
            "personal_access_tokens": {
                (True, ("token",)), (False, ("expires_at",)),
                (False, ("revoked_at",)),
                (False, ("tokenable_type", "tokenable_id")),
            },
            "password_reset_tokens": {
                (False, ("created_at",)), (False, ("token",)),
            },
        }
        for table, required in expected.items():
            with self.subTest(table=table):
                indexes = await self.connection.select(
                    'SELECT name, "unique" FROM pragma_index_list(:table)',
                    {"table": table},
                )
                actual = set()
                for index in indexes:
                    columns = await self.connection.select(
                        "SELECT name FROM pragma_index_info(:index) "
                        "ORDER BY seqno",
                        {"index": index["name"]},
                    )
                    actual.add((
                        bool(index["unique"]),
                        tuple(column["name"] for column in columns),
                    ))
                self.assertLessEqual(required, actual)

    async def testAuthorizationForeignKeysAndCompositeKeysAreEnforced(
        self,
    ) -> None:
        """Reject orphan and duplicate bindings while allowing distinct owners."""
        await self.connection.execute(
            "INSERT INTO permissions (id, name) VALUES (1, 'edit')",
        )
        await self.connection.execute(
            "INSERT INTO roles (id, name) VALUES (1, 'editor')",
        )
        bindings = (
            ("model_has_permissions", "permission_id"),
            ("model_has_roles", "role_id"),
        )
        for table, foreign_key in bindings:
            with self.subTest(table=table):
                query = (
                    f"INSERT INTO {table} "  # noqa: S608
                    f"({foreign_key}, model_id, model_type) "
                    "VALUES (:parent, :owner, :type)"
                )
                values = {"parent": 1, "owner": "42", "type": "User"}
                await self.connection.execute(query, values)
                await self.connection.execute(query, {**values, "type": "Bot"})
                with self.assertRaises(QueryException):
                    await self.connection.execute(query, values)
                with self.assertRaises(QueryException):
                    await self.connection.execute(query, {**values, "parent": 2})
        query = (
            "INSERT INTO role_has_permissions (permission_id, role_id) "
            "VALUES (:permission, :role)"
        )
        await self.connection.execute(query, {"permission": 1, "role": 1})
        for permission, role in ((1, 1), (2, 1), (1, 2)):
            with (
                self.subTest(permission=permission, role=role),
                self.assertRaises(QueryException),
            ):
                await self.connection.execute(
                    query, {"permission": permission, "role": role},
                )
        for table in ("permissions", "roles"):
            with self.subTest(table=table), self.assertRaises(QueryException):
                await self.connection.execute(
                    f"DELETE FROM {table} WHERE id = 1",  # noqa: S608
                )

    async def testUserCrudCastsDefaultsAndHiddenAttributes(self) -> None:
        """Persist the real User model with its existing attribute policies."""
        user = await User.create({
            "name": "Ada", "email": "ada@example.test", "password": "digest",
        })
        self.assertIsInstance(user.id, int)
        loaded = await User.find(user.id)
        self.assertIsNotNone(loaded)
        self.assertIs(loaded.active, True)
        self.assertIsInstance(loaded.created_at, datetime)
        self.assertIsInstance(loaded.updated_at, datetime)
        self.assertTrue(await loaded.update({"name": "Ada Lovelace"}))
        loaded.email_verified_at = "2026-09-28T10:30:00"
        loaded.remember_token = "remember-digest"  # noqa: S105
        loaded.active = 0
        self.assertTrue(await loaded.save())
        updated = await User.find(user.id)
        self.assertEqual(updated.name, "Ada Lovelace")
        self.assertIs(updated.active, False)
        self.assertEqual(updated.email_verified_at, datetime(2026, 9, 28, 10, 30))
        self.assertEqual(updated.password, "digest")
        serialized = updated.toDict()
        self.assertNotIn("password", serialized)
        self.assertNotIn("remember_token", serialized)
        self.assertEqual(serialized["email"], "ada@example.test")
        with self.assertRaises(QueryException):
            await User.create({
                "name": "Duplicate", "email": "ada@example.test",
                "password": "digest",
            })
        self.assertTrue(await updated.delete())
        self.assertIsNone(await User.find(user.id))

    async def testUserMassAssignmentStillProtectsSensitiveColumns(self) -> None:
        """Reject every column outside the model's explicit fillable list."""
        for attribute in (
            "id", "active", "email_verified_at", "remember_token",
            "created_at", "updated_at", "unknown_column",
        ):
            with (
                self.subTest(attribute=attribute),
                self.assertRaises(MassAssignmentException),
            ):
                await User.create({attribute: "untrusted"})
        self.assertEqual(await User.query().count(), 0)

    async def testHistoricalMigrationKeepsItsVersionWhenUserSchemaChanges(
        self,
    ) -> None:
        """Replay users V1 after the active model points at newer metadata."""
        self.assertIs(User.__meta__.table, USERS_V1)
        migration = self.migrations[4]
        module = import_module(type(migration).__module__)
        self.assertIs(module.USERS_V1, USERS_V1)
        newer = replace(
            USERS_V1,
            columns={**USERS_V1.columns, "nickname": String(80).nullable()},
        )
        with (
            patch.object(User, "__meta__", replace(User.__meta__, table=newer)),
            patch.object(User, "table_definition", newer),
            migration_connection_scope(self.connection),
        ):
            await migration.down()
            await migration.up()
        columns = await self.connection.select("PRAGMA table_info(users)")
        self.assertEqual(
            tuple(row["name"] for row in columns), _TABLE_COLUMNS["users"],
        )
        self.assertIs(User.__meta__.table, USERS_V1)
