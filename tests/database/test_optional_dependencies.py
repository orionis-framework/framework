import subprocess
import sys
from pathlib import Path
from orionis.test import TestCase

class TestPostgresqlOptionalDependency(TestCase):
    """Keep PostgreSQL optional regardless of locally installed drivers."""

    def testMissingAsyncpgFailsOnlyWhenBackendIsUsed(self) -> None:
        """Import core modules and execute SQLite while PostgreSQL is unavailable.

        Returns
        -------
        None
            PostgreSQL reports its extra on first use without breaking SQLite.
        """
        script = """import asyncio
import importlib.abc
import sys

class MissingAsyncpg(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] == 'asyncpg':
            raise ModuleNotFoundError('Optional driver unavailable', name=fullname)
        return None

sys.meta_path.insert(0, MissingAsyncpg())
import orionis.foundation
import orionis.orm
from orionis.database import Connection, Migrator, SeederRunner
from orionis.database.exceptions import MissingDatabaseDependencyException

assert 'asyncpg' not in sys.modules
pgsql = Connection('pgsql', {'driver': 'pgsql', 'database': 'orionis'})
assert pgsql._engine is None

async def check_backends():
    sqlite = Connection('sqlite', {'driver': 'sqlite', 'database': ':memory:'})
    try:
        assert await sqlite.select('SELECT 1 AS value') == [{'value': 1}]
        try:
            await pgsql.select('SELECT 1')
        except MissingDatabaseDependencyException as error:
            assert "uv add 'orionis[pgsql]'" in str(error)
            assert error.__cause__.name == 'asyncpg'
        else:
            raise AssertionError('The missing PostgreSQL extra was not reported')
        assert await sqlite.select('SELECT 2 AS value') == [{'value': 2}]
    finally:
        await pgsql.disconnect()
        await sqlite.disconnect()

asyncio.run(check_backends())
print('PostgreSQL isolation passed')
"""
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-B", "-c", script],
            cwd=Path(__file__).resolve().parents[2],
            check=False, capture_output=True, text=True, encoding="utf-8",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PostgreSQL isolation passed", result.stdout)
