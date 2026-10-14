from __future__ import annotations
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

class TestLazyConsumers(unittest.TestCase):
    """Keep unused implementations out of real registration and runtime paths."""

    # ruff: noqa: S603

    def _probe(self, source: str) -> None:
        """Run isolated assertions and report child-process diagnostics.

        Parameters
        ----------
        source : str
            Python statements to dedent and execute in a fresh interpreter.

        Returns
        -------
        None
            Assert successful execution with captured output on failure.
        """
        result = subprocess.run(
            [sys.executable, "-B", "-c", textwrap.dedent(source)],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def testTestingProviderDefersItsImplementationUntilRegistration(self) -> None:
        """Verify testing metadata defers the runner until registration.

        Returns
        -------
        None
            Assert deferred imports, repeated bindings and constructor annotations.
        """
        self._probe("""
            import sys
            from types import SimpleNamespace
            from typing import get_type_hints
            from orionis.test.provider import TestingProvider
            from orionis.test.contracts.engine import ITestingEngine
            from orionis.foundation.contracts.application import IApplication
            assert TestingProvider.provides() == [ITestingEngine]
            assert 'orionis.test.core.engine' not in sys.modules
            assert 'unittest' not in sys.modules
            bindings = []
            provider = TestingProvider(SimpleNamespace(
                singleton=lambda contract, concrete: bindings.append(
                    (contract, concrete),
                ),
            ))
            provider.register()
            provider.register()
            from orionis.test.core.engine import TestingEngine
            assert bindings == [(ITestingEngine, TestingEngine)] * 2
            assert get_type_hints(TestingEngine.__init__)['app'] is IApplication
        """)

    def testMemorySchedulerStoreDoesNotImportDatabaseOrRedisBackends(self) -> None:
        """Verify memory scheduler metadata without importing unused backends.

        Returns
        -------
        None
            Assert annotations, configuration errors and unloaded libraries.
        """
        self._probe("""
            import sys
            from types import SimpleNamespace
            from typing import get_type_hints
            from orionis.console.tasks.store import ScheduleStore
            from orionis.database.contracts.connection_manager import IConnectionManager
            app = SimpleNamespace(config=lambda name: {
                'store': 'memory', 'stores': {'redis': None, 'database': None},
            })
            store = ScheduleStore(app, None)
            assert store.store == 'memory'
            hints = get_type_hints(ScheduleStore.__init__)
            assert hints['db_manager'] is IConnectionManager
            for factory in (store.redis, store.database):
                try:
                    factory()
                except RuntimeError as error:
                    assert 'not configured' in str(error)
                else:
                    raise AssertionError('Missing backend configuration must fail')
            for module in ('redis', 'sqlalchemy', 'apscheduler'):
                assert module not in sys.modules, module
        """)

    def testScheduleConstructionDefersSchedulerAndTriggerImplementations(self) -> None:
        """Verify schedule construction defers scheduler and trigger imports.

        Returns
        -------
        None
            Assert the schedule remains stopped and implementations unloaded.
        """
        self._probe("""
            import sys
            from types import SimpleNamespace
            from orionis.console.tasks.schedule import Schedule
            stores = SimpleNamespace(
                store='memory', config=SimpleNamespace(store='memory'),
            )
            schedule = Schedule(None, None, stores)
            assert schedule.isStopped()
            assert 'apscheduler' not in sys.modules
            assert 'orionis.console.fluent.task' not in sys.modules
        """)

    def testSchedulerBackendsLoadOnlyWhenTheirFactoryIsRequested(self) -> None:
        """Verify each scheduler factory loads only its selected backend.

        Returns
        -------
        None
            Assert native store types and isolation of unused backends.
        """
        self._probe("""
            import sys
            from types import SimpleNamespace
            from orionis.console.tasks.store import ScheduleStore
            store = ScheduleStore(SimpleNamespace(config=lambda name: {
                'store': 'redis', 'stores': {'redis': {}},
            }), None)
            assert 'redis' not in sys.modules
            backend = store.redis()
            from apscheduler.jobstores.redis import RedisJobStore
            assert type(backend) is RedisJobStore
            assert 'sqlalchemy' not in sys.modules
            backend.shutdown()
        """)
        self._probe("""
            import sys
            from types import SimpleNamespace
            from orionis.console.tasks.store import ScheduleStore
            app = SimpleNamespace(config=lambda name: {
                'store': 'database', 'stores': {'database': {}},
            })
            manager = SimpleNamespace(configFor=lambda name: {
                'driver': 'sqlite', 'database': ':memory:',
            })
            store = ScheduleStore(app, manager)
            assert 'sqlalchemy' not in sys.modules
            backend = store.database()
            from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
            assert type(backend) is SQLAlchemyJobStore
            assert 'redis' not in sys.modules
            assert 'sqlalchemy.dialects.oracle' not in sys.modules
            backend.shutdown()
        """)

    def testMcpMetadataDoesNotLoadUnusedRuntimeImplementations(self) -> None:
        """Verify local MCP metadata defers transports and routing imports.

        Returns
        -------
        None
            Assert annotations, compiled-server caching and unknown-name errors.
        """
        self._probe("""
            import asyncio
            import sys
            from typing import get_type_hints
            from orionis.mcp.manager import McpManager
            from orionis.mcp.config import McpConfig
            from orionis.mcp.server.compiler import CompiledMcpServer
            from orionis.mcp.server.primitives import Server
            hints = get_type_hints(McpManager.getLocalServer)
            assert hints['return'] is CompiledMcpServer
            assert 'orionis.http.request' not in sys.modules
            assert 'orionis.schemas.validator' not in sys.modules
            manager = McpManager(None, None, McpConfig(), None)
            class LocalServer(Server):
                name = 'Local'
                version = '1.0.0'
            manager.local('local', LocalServer)
            compiled = manager.getLocalServer('local')
            assert compiled.definition is LocalServer
            assert manager.getLocalServer('local') is compiled
            try:
                asyncio.run(manager.startLocal('missing'))
            except KeyError:
                pass
            else:
                raise AssertionError('Unknown local names must fail')
            assert 'orionis.mcp.transport.http' not in sys.modules
            assert 'orionis.mcp.transport.stdio' not in sys.modules
            assert 'orionis.mcp.routing' not in sys.modules
        """)

    def testMarkdownFilterRegistrationDefersMarkdownUntilRendering(self) -> None:
        """Verify filter registration defers Markdown until rendering.

        Returns
        -------
        None
            Assert rendered markup and reuse of the loaded Markdown module.
        """
        self._probe("""
            import sys
            from orionis.view.filters import _filter_markdown
            render = _filter_markdown()
            assert 'markdown' not in sys.modules
            assert '<strong>hello</strong>' in render('**hello**')
            markdown = sys.modules['markdown']
            assert '<em>again</em>' in render('*again*')
            assert sys.modules['markdown'] is markdown
        """)

    def testJsonParsingDefersXmlWithoutChangingXmlSecurity(self) -> None:
        """Verify JSON parsing defers XML imports without weakening XML security.

        Returns
        -------
        None
            Assert parsing results and rejection of XML entity expansion.
        """
        self._probe("""
            import sys
            from orionis.http.payload.parsers import parse_json, parse_xml
            assert parse_json(b'{"value": 1}') == {'value': 1}
            assert 'defusedxml' not in sys.modules
            assert parse_xml(b'<root>value</root>').text == 'value'
            from defusedxml.common import EntitiesForbidden
            try:
                parse_xml(b'<!DOCTYPE root [<!ENTITY x "unsafe">]><root>&x;</root>')
            except EntitiesForbidden:
                pass
            else:
                raise AssertionError('XML entity expansion must remain forbidden')
        """)

    def testHttpKernelImportDoesNotSelectGranianOrRedis(self) -> None:
        """Verify HTTP kernel imports support an ASGI-only runtime.

        Returns
        -------
        None
            Assert application annotations and unloaded server backends.
        """
        self._probe("""
            import sys
            from typing import get_type_hints
            from orionis.http.kernel import KernelHTTP
            from orionis.foundation.contracts.application import IApplication
            assert get_type_hints(KernelHTTP.__init__)['app'] is IApplication
            assert 'granian' not in sys.modules
            assert 'redis' not in sys.modules
            assert 'orionis.http.adapters.websocket.rsgi' not in sys.modules
        """)

    def testServerCommandDiscoveryDoesNotImportItsServerSdk(self) -> None:
        """Verify serve command discovery defers server SDK imports.

        Returns
        -------
        None
            Assert command metadata and Granian loading during interface selection.
        """
        self._probe("""
            import sys
            from orionis.console.commands.serve.serve import ServerCommand
            command = ServerCommand()
            assert command.signature == 'serve'
            assert 'granian' not in sys.modules
            assert 'anyio' not in sys.modules
            command._ServerCommand__appendInterfaceToCommand()
            assert command._ServerCommand__env['GRANIAN_INTERFACE'] == 'rsgi'
            assert 'granian' in sys.modules
        """)

    def testCoreCommandDiscoveryKeepsBackendSdksUnloaded(self) -> None:
        """Verify core command discovery leaves backend SDKs unloaded.

        Returns
        -------
        None
            Assert DI metadata, cache-clear output and error propagation.
        """
        self._probe("""
            import asyncio
            import sys
            from types import SimpleNamespace
            from typing import get_type_hints
            from orionis.console.core.commands import CORE_COMMANDS
            from orionis.console.commands.migrate.migrate import MigrateCommand
            from orionis.console.commands.support.clear_cache import ClearCacheCommand
            from orionis.database.migrations.migrator import Migrator
            assert MigrateCommand in CORE_COMMANDS
            assert get_type_hints(MigrateCommand.handle)['migrator'] is Migrator
            async def clear():
                \"\"\"Report a successful cache clear.

                Returns
                -------
                bool
                    Indicate successful cache clearing.
                \"\"\"
                return True
            output = []
            console = SimpleNamespace(success=lambda *args, **kw: output.append(args))
            command = ClearCacheCommand()
            assert asyncio.run(command.handle(
                SimpleNamespace(clear=clear), console,
            )) == 0
            assert len(output) == 1
            failure = ValueError('Unexpected cache failure')
            async def fail():
                \"\"\"Raise the configured cache-clear failure.

                Returns
                -------
                None
                    Never return normally.

                Raises
                ------
                ValueError
                    Always raise the configured failure.
                \"\"\"
                raise failure
            try:
                asyncio.run(command.handle(SimpleNamespace(clear=fail), console))
            except ValueError as error:
                assert error is failure
            else:
                raise AssertionError('Programming errors must still propagate')
            for name in ('sqlalchemy', 'redis', 'aiomcache', 'granian', 'apscheduler'):
                assert name not in sys.modules, name
        """)

    def testMemoryRateLimiterAndDisabledLimiterKeepRedisUnloaded(self) -> None:
        """Verify memory and disabled limiters leave Redis unloaded.

        Returns
        -------
        None
            Assert limiter behavior, cleanup and memory-store error propagation.
        """
        self._probe("""
            import asyncio
            import sys
            from types import SimpleNamespace
            from orionis.http.layer.shared.rate_limit import RateLimitMiddleware
            async def check():
                \"\"\"Exercise memory and disabled rate limiters.

                Returns
                -------
                None
                    Assert handling, cleanup and memory-store error propagation.
                \"\"\"
                adapter = SimpleNamespace(client=lambda: '192.0.2.1')
                memory = RateLimitMiddleware({'rate_limit_enabled': True}, None)
                assert await memory.handle(adapter) is None
                await memory.close()
                failure = RuntimeError('memory storage failed')
                class BrokenStore:
                    async def hit(self, *args):
                        \"\"\"Raise the configured memory-store failure.

                        Parameters
                        ----------
                        *args : object
                            Unused rate-limit arguments.

                        Returns
                        -------
                        None
                            Never return normally.

                        Raises
                        ------
                        RuntimeError
                            Always raise the configured failure.
                        \"\"\"
                        raise failure
                memory._RateLimitMiddleware__store = BrokenStore()
                try:
                    await memory.handle(adapter)
                except RuntimeError as error:
                    assert error is failure
                else:
                    raise AssertionError('Memory backend failures must propagate')
                disabled = RateLimitMiddleware({'rate_limit_store': 'redis'}, None)
                assert await disabled.handle(adapter) is None
                await disabled.close()
            asyncio.run(check())
            assert 'redis' not in sys.modules
            assert 'orionis.http.layer.store.redis_rate_limit' not in sys.modules
        """)
