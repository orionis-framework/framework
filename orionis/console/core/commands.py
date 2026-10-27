from orionis.console.commands.bootstrap.config import BootstrapConfigCommand
from orionis.console.commands.bootstrap.lifespan import BootstrapLifespanCommand
from orionis.console.commands.bootstrap.routes import (
    BootstrapAiCommand,
    BootstrapApiCommand,
    BootstrapConsoleCommand,
    BootstrapWebCommand,
    BootstrapWebsocketCommand,
)
from orionis.console.commands.db.seed import DbSeedCommand
from orionis.console.commands.db.show import DbShowCommand
from orionis.console.commands.db.table import DbTableCommand
from orionis.console.commands.db.wipe import DbWipeCommand
from orionis.console.commands.make.console import MakeConsoleCommand
from orionis.console.commands.make.console_listener import MakeConsoleListener
from orionis.console.commands.make.contract import MakeContract
from orionis.console.commands.make.database_migration import MakeDatabaseMigration
from orionis.console.commands.make.database_schema import MakeDatabaseSchema
from orionis.console.commands.make.database_seeder import MakeDatabaseSeeder
from orionis.console.commands.make.facade import MakeFacade
from orionis.console.commands.make.factory import MakeFactory
from orionis.console.commands.make.http_controller import MakeHttpController
from orionis.console.commands.make.http_middleware import MakeHttpMiddleware
from orionis.console.commands.make.http_schema import MakeHttpSchema
from orionis.console.commands.make.http_schema_rule import MakeHttpSchemaRule
from orionis.console.commands.make.job import MakeJob
from orionis.console.commands.make.mail import MakeMail
from orionis.console.commands.make.mcp import (
    MakeMcpPrompt,
    MakeMcpResource,
    MakeMcpServer,
    MakeMcpTool,
)
from orionis.console.commands.make.model import MakeModel
from orionis.console.commands.make.provider import MakeProvider
from orionis.console.commands.make.realtime import MakeRealtimeHub, MakeRealtimeSocket
from orionis.console.commands.make.service import MakeService
from orionis.console.commands.make.test import MakeTest
from orionis.console.commands.mcp.list import McpListCommand
from orionis.console.commands.mcp.start import McpStartCommand
from orionis.console.commands.migrate.fresh import MigrateFreshCommand
from orionis.console.commands.migrate.migrate import MigrateCommand
from orionis.console.commands.migrate.refresh import MigrateRefreshCommand
from orionis.console.commands.migrate.reset import MigrateResetCommand
from orionis.console.commands.migrate.rollback import MigrateRollbackCommand
from orionis.console.commands.migrate.status import MigrateStatusCommand
from orionis.console.commands.queue.clear import QueueClearCommand
from orionis.console.commands.queue.failed import QueueFailedCommand
from orionis.console.commands.queue.forget import QueueForgetCommand
from orionis.console.commands.queue.migrate import QueueMigrateCommand
from orionis.console.commands.queue.retry import QueueRetryCommand
from orionis.console.commands.queue.work import QueueWorkCommand
from orionis.console.commands.route.list import RouteListCommand
from orionis.console.commands.schedule.list import ScheduleListCommand
from orionis.console.commands.schedule.work import ScheduleWorkCommand
from orionis.console.commands.seed.seed import SeedCommand
from orionis.console.commands.serve.serve import ServerCommand
from orionis.console.commands.support.about import VersionCommand
from orionis.console.commands.support.clear_cache import ClearCacheCommand
from orionis.console.commands.support.clear_logs import ClearLogsCommand
from orionis.console.commands.support.clear_testing import ClearTestingCommand
from orionis.console.commands.support.clear_views import ClearViewsCommand
from orionis.console.commands.support.down import DownCommand
from orionis.console.commands.support.environment import EnvironmentCommand
from orionis.console.commands.support.install import InstallCommand
from orionis.console.commands.support.key_generate import KeyGenerateCommand
from orionis.console.commands.support.list import HelpCommand
from orionis.console.commands.support.optimize import OptimizeCommand
from orionis.console.commands.support.optimize_clear import OptimizeClearCommand
from orionis.console.commands.support.up import UpCommand
from orionis.console.commands.test.test import TestCommand

def get_core_commands_mapping() -> tuple[type, ...]:
    """
    Return the immutable collection of core command classes.

    Returns
    -------
    tuple[type, ...]
        Immutable collection of command classes registered by the framework.
    """
    # Return the command classes registered by the framework.
    return (
        BootstrapApiCommand,
        BootstrapAiCommand,
        BootstrapConsoleCommand,
        BootstrapWebCommand,
        BootstrapWebsocketCommand,
        BootstrapConfigCommand,
        BootstrapLifespanCommand,
        OptimizeClearCommand,
        OptimizeCommand,
        KeyGenerateCommand,
        EnvironmentCommand,
        DownCommand,
        UpCommand,
        ClearViewsCommand,
        ClearCacheCommand,
        ClearLogsCommand,
        ClearTestingCommand,
        HelpCommand,
        InstallCommand,
        MakeConsoleCommand,
        MakeFacade,
        MakeProvider,
        MakeConsoleListener,
        MakeContract,
        MakeService,
        MakeModel,
        MakeMcpServer,
        MakeMcpTool,
        MakeMcpResource,
        MakeMcpPrompt,
        McpStartCommand,
        McpListCommand,
        MakeFactory,
        MakeMail,
        MakeJob,
        MakeHttpController,
        MakeHttpMiddleware,
        MakeHttpSchema,
        MakeHttpSchemaRule,
        MakeRealtimeSocket,
        MakeRealtimeHub,
        MakeDatabaseMigration,
        MakeDatabaseSeeder,
        MakeDatabaseSchema,
        MakeTest,
        DbSeedCommand,
        DbShowCommand,
        DbTableCommand,
        DbWipeCommand,
        MigrateCommand,
        MigrateFreshCommand,
        MigrateRefreshCommand,
        MigrateResetCommand,
        MigrateRollbackCommand,
        MigrateStatusCommand,
        SeedCommand,
        ScheduleListCommand,
        ScheduleWorkCommand,
        QueueMigrateCommand,
        QueueWorkCommand,
        QueueFailedCommand,
        QueueRetryCommand,
        QueueForgetCommand,
        QueueClearCommand,
        RouteListCommand,
        TestCommand,
        VersionCommand,
        ServerCommand,
    )

CORE_COMMANDS: tuple = get_core_commands_mapping()
