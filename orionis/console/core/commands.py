from orionis.console.commands.make.make_provider import MakeProvider
from orionis.console.commands.make.task_listener_command import MakeTaskListener
from orionis.console.commands.migrate.fresh_command import MigrateFreshCommand
from orionis.console.commands.migrate.migrate_command import MigrateCommand
from orionis.console.commands.migrate.refresh_command import MigrateRefreshCommand
from orionis.console.commands.migrate.reset_command import MigrateResetCommand
from orionis.console.commands.migrate.rollback_command import MigrateRollbackCommand
from orionis.console.commands.migrate.status_command import MigrateStatusCommand
from orionis.console.commands.support.optimize import OptimizeCommand
from orionis.console.commands.support.optimize_clear import OptimizeClearCommand
from orionis.console.commands.support.list import HelpCommand
from orionis.console.commands.support.about import VersionCommand
from orionis.console.commands.make.make_command import MakeCommand
from orionis.console.commands.schedule.list_command import ScheduleListCommand
from orionis.console.commands.schedule.work_command import ScheduleWorkCommand
from orionis.console.commands.serve.serve_command import ServerCommand
from orionis.console.commands.test.test_command import TestCommand

def get_core_commands_mapping() -> tuple:
    """
    Return a read-only mapping of core command classes.

    Returns
    -------
    tuple
        An immutable tuple of core command classes.
    """
    # Create an immutable mapping of core command classes for the framework.
    return (
        OptimizeClearCommand,
        OptimizeCommand,
        HelpCommand,
        MakeCommand,
        MakeProvider,
        MakeTaskListener,
        MigrateCommand,
        MigrateFreshCommand,
        MigrateRefreshCommand,
        MigrateResetCommand,
        MigrateRollbackCommand,
        MigrateStatusCommand,
        ScheduleListCommand,
        ScheduleWorkCommand,
        TestCommand,
        VersionCommand,
        ServerCommand,
    )

CORE_COMMANDS: tuple = get_core_commands_mapping()
