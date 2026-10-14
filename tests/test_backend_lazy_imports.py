import subprocess
import sys
import unittest
from pathlib import Path

class TestBackendLazyImports(unittest.TestCase):
    """Exercise backend selection in fresh interpreters with empty module caches."""

    # ruff: noqa: S603

    def _check(self, script: str) -> None:
        """Run an isolated import scenario and report child diagnostics.

        Parameters
        ----------
        script : str
            Python statements to execute in a fresh interpreter.

        Returns
        -------
        None
            Assert successful execution with captured output on failure.
        """
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            check=False,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def testProviderDiscoveryDoesNotLoadImplementations(self) -> None:
        """Verify provider discovery leaves services and backends unloaded.

        Returns
        -------
        None
            Assert provider contracts and unloaded implementations.
        """
        self._check("""
import sys
from orionis.cache.provider import CacheProvider
from orionis.database.provider import ConnectionManagerProvider
from orionis.encrypter.provider import EncrypterProvider
from orionis.hashing.provider import HashProvider
from orionis.storage.provider import StorageProvider
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.storage.contracts.manager import IStorageManager

assert CacheProvider.provides() == [ICacheManager]
assert StorageProvider.provides() == [IStorageManager]
for module in ('orionis.cache.cache_manager', 'orionis.database.connection_manager',
               'orionis.encrypter.encrypter', 'orionis.hashing.hash_manager',
               'orionis.storage.manager', 'sqlalchemy', 'cryptography', 'pwdlib',
               'redis', 'aiocache'):
    assert module not in sys.modules, module
""")

    def testFileCacheOperationsAndSubclassLocksKeepOtherStoresUnloaded(self) -> None:
        """Verify file cache operations and subclass locks defer other stores.

        Returns
        -------
        None
            Assert cache reuse, replacement, locking and backend isolation.
        """
        self._check("""
import asyncio
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from orionis.cache import CacheManager, CacheRepository

assert not any(name.startswith('orionis.cache.stores.') for name in sys.modules)

class App:
    def __init__(self, root):
        \"\"\"Store the application root.

        Parameters
        ----------
        root : Path
            Base directory for file-cache storage.

        Returns
        -------
        None
            Initialize the test double.
        \"\"\"
        self.basePath = root
    def config(self, section):
        \"\"\"Return the file-cache configuration.

        Parameters
        ----------
        section : str
            Unused configuration section name.

        Returns
        -------
        SimpleNamespace
            File-cache defaults with a prefix and no explicit stores.
        \"\"\"
        return SimpleNamespace(default='file', prefix='lazy', stores=SimpleNamespace())

async def check(root):
    \"\"\"Exercise file-cache operations and subclass locks.

    Parameters
    ----------
    root : Path
        Temporary directory for cache storage.

    Returns
    -------
    None
        Assert repository reuse, replacement and locked reads and writes.
    \"\"\"
    manager = CacheManager(App(root))
    repository = manager.store()
    assert manager.store() is repository
    assert await repository.set('key', 'before')
    assert await repository.replace('key', 'after')
    async with repository.lock('key'):
        assert await repository.get('key') == 'after'

    from orionis.cache.stores.file import FileCacheBackend
    class CustomFileBackend(FileCacheBackend):
        pass
    custom = CacheRepository(CustomFileBackend(root / 'custom'))
    async with custom.lock('key'):
        assert await custom.set('key', 42)
    assert await custom.get('key') == 42

with TemporaryDirectory() as directory:
    asyncio.run(check(Path(directory)))

for module in ('aiocache', 'redis', 'sqlalchemy', 'orionis.cache.stores.database',
               'orionis.cache.stores.memory', 'orionis.cache.stores.redis',
               'orionis.cache.stores.memcached'):
    assert module not in sys.modules, module
""")

    def testMemorySessionDoesNotLoadPersistentStores(self) -> None:
        """Verify memory sessions leave persistent stores unloaded.

        Returns
        -------
        None
            Assert memory-store selection and isolation of persistent backends.
        """
        self._check("""
import sys
from pathlib import Path
from orionis.session.manager import SessionManager

assert not any(name.startswith('orionis.session.stores.') for name in sys.modules)
class App:
    basePath = Path('.')
    def config(self, section):
        \"\"\"Return the memory-session configuration.

        Parameters
        ----------
        section : str
            Unused configuration section name.

        Returns
        -------
        dict[str, str]
            Configuration selecting the memory session driver.
        \"\"\"
        return {'driver': 'memory'}

SessionManager(App(), object())
assert 'orionis.session.stores.memory' in sys.modules
for module in ('orionis.session.stores.database', 'orionis.session.stores.file',
               'orionis.session.stores.cache', 'orionis.orm.resolver',
               'sqlalchemy', 'aiocache', 'redis', 'cryptography', 'filelock'):
    assert module not in sys.modules, module
""")

    def testMemoryStorageLoadsOnlySelectedDriver(self) -> None:
        """Verify memory storage loads only the selected driver.

        Returns
        -------
        None
            Assert disk caching and unloaded cloud drivers and SDKs.
        """
        self._check("""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from orionis.storage import StorageManager

assert not any(name.startswith('orionis.storage.drivers.') for name in sys.modules)
class App:
    basePath = Path('.')
    def config(self, section):
        \"\"\"Return the memory-storage configuration.

        Parameters
        ----------
        section : str
            Unused configuration section name.

        Returns
        -------
        SimpleNamespace
            Default memory disk with no public URL.
        \"\"\"
        disk = SimpleNamespace(driver='memory', url=None)
        return SimpleNamespace(default='memory', disks=SimpleNamespace(memory=disk))

manager = StorageManager(App())
disk = manager.disk()
assert manager.disk() is disk
assert 'orionis.storage.drivers.memory' in sys.modules
for module in ('orionis.storage.drivers.azure', 'orionis.storage.drivers.s3',
               'orionis.storage.drivers.gcs', 'orionis.storage.drivers.local',
               'boto3', 'azure', 'google.cloud.storage'):
    assert module not in sys.modules, module
""")

    def testSyncQueueDoesNotLoadDurableBackends(self) -> None:
        """Verify synchronous queues leave durable backends unloaded.

        Returns
        -------
        None
            Assert driver caching and isolation of durable queue implementations.
        """
        self._check("""
import asyncio
import sys
from orionis.queues.manager import QueueManager
from orionis.queues.serializer import JobSerializer

class App:
    def config(self, section):
        \"\"\"Return the synchronous-queue configuration.

        Parameters
        ----------
        section : str
            Unused configuration section name.

        Returns
        -------
        dict[str, str]
            Configuration selecting the synchronous queue driver.
        \"\"\"
        return {'default': 'sync'}

manager = QueueManager(App(), JobSerializer())
async def check():
    \"\"\"Verify synchronous queue-driver caching.

    Returns
    -------
    None
        Assert repeated connections reuse the selected driver.
    \"\"\"
    driver = await manager.connection()
    assert await manager.connection() is driver
asyncio.run(check())

assert 'orionis.queues.drivers.sync' in sys.modules
for module in ('orionis.queues.drivers.database', 'orionis.queues.drivers.redis',
               'orionis.queues.failed.repository',
               'sqlalchemy', 'redis', 'cryptography'):
    assert module not in sys.modules, module
""")

    def testDatabaseManagerDefersEngineUntilConnectionResolution(self) -> None:
        """Verify database connection resolution defers SQLAlchemy imports.

        Returns
        -------
        None
            Assert annotations, connection caching, query results and driver isolation.
        """
        self._check("""
import asyncio
import sys
from typing import get_type_hints
from orionis.database import ConnectionManager
from orionis.foundation.contracts.application import IApplication

class App:
    def config(self, section):
        \"\"\"Return the in-memory SQLite configuration.

        Parameters
        ----------
        section : str
            Unused configuration section name.

        Returns
        -------
        dict[str, object]
            Default SQLite connection using an in-memory database.
        \"\"\"
        return {'default': 'sqlite',
                'connections': {'sqlite': {'driver': 'sqlite', 'database': ':memory:'}}}

manager = ConnectionManager(App())
assert get_type_hints(ConnectionManager.__init__)['app'] is IApplication
assert 'sqlalchemy' not in sys.modules
connection = manager.connection()
assert manager.connection() is connection
assert 'sqlalchemy' in sys.modules
assert 'sqlalchemy.dialects.oracle' not in sys.modules

async def check():
    \"\"\"Verify a SQLite query and disconnect the connection.

    Returns
    -------
    None
        Assert the selected value and release the connection.
    \"\"\"
    try:
        assert await connection.select('SELECT 1 AS value') == [{'value': 1}]
    finally:
        await connection.disconnect()
asyncio.run(check())

for module in ('asyncpg', 'aiomysql', 'oracledb', 'aioodbc', 'pyodbc',
               'redshift_connector', 'sqlalchemy_redshift'):
    assert module not in sys.modules, module
""")

    def testHashingSymbolsAndDriversDeferPasswordLibraries(self) -> None:
        """Verify hasher selection defers password-library imports.

        Returns
        -------
        None
            Assert Argon2 selection, driver caching and unloaded password backends.
        """
        self._check("""
import sys
from types import SimpleNamespace
from orionis.hashing import HashManager

assert 'orionis.hashing.hashers.argon2_hasher' not in sys.modules
assert 'orionis.hashing.hashers.bcrypt_hasher' not in sys.modules
class App:
    def config(self, section):
        \"\"\"Return the password-hashing configuration.

        Parameters
        ----------
        section : str
            Unused configuration section name.

        Returns
        -------
        SimpleNamespace
            Argon2 defaults and low-cost backend settings for the probe.
        \"\"\"
        return SimpleNamespace(driver='argon2', argon2=SimpleNamespace(memory=8,
                               threads=1, time=1), bcrypt=SimpleNamespace(rounds=4))

manager = HashManager(App())
hasher = manager.driver()
from orionis.hashing import Argon2Hasher
assert isinstance(hasher, Argon2Hasher)
assert manager.driver() is hasher
assert 'orionis.hashing.hashers.bcrypt_hasher' not in sys.modules
for module in ('pwdlib', 'argon2', 'bcrypt'):
    assert module not in sys.modules, module
""")

    def testMailManagerDoesNotLoadUnusedTransports(self) -> None:
        """Verify mail-manager construction leaves unused transports unloaded.

        Returns
        -------
        None
            Assert SMTP and file transport implementations remain unloaded.
        """
        self._check("""
import sys
from orionis.mail.manager import MailManager

MailManager(object(), object())
for module in ('orionis.mail.transports.file', 'orionis.mail.transports.smtp',
               'smtplib'):
    assert module not in sys.modules, module
""")

    def testRuntimeConstructorAnnotationsStillSupportInjection(self) -> None:
        """Verify deferred runtime annotations preserve container injection.

        Returns
        -------
        None
            Assert runtime type hints and application injection into a cache manager.
        """
        self._check("""
import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import get_type_hints
from unittest.mock import Mock
from orionis.cache import CacheManager
from orionis.container.container import Container
from orionis.foundation.contracts.application import IApplication
from orionis.session.manager import SessionManager
from orionis.cache.contracts.cache_manager import ICacheManager
from orionis.queues.manager import QueueManager
from orionis.queues.worker import Worker

assert get_type_hints(CacheManager.__init__)['app'] is IApplication
assert get_type_hints(SessionManager.__init__)['app'] is IApplication
assert get_type_hints(SessionManager.__init__)['cache'] is ICacheManager
assert get_type_hints(QueueManager.worker)['return'] is Worker
async def check():
    \"\"\"Build a cache manager through the service container.

    Returns
    -------
    None
        Assert the manager receives the registered application.
    \"\"\"
    app = Mock(spec=IApplication)
    app.basePath = Path('.')
    app.config.return_value = SimpleNamespace(default='memory', prefix='',
                                            stores=SimpleNamespace())
    container = Container()
    container.instance(IApplication, app)
    manager = await container.build(CacheManager)
    assert manager._app is app
asyncio.run(check())
""")
