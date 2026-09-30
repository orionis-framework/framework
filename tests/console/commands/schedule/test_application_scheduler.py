from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from app.console.commands.inspire_command import InspireCommand
from app.console.scheduler import Scheduler
from orionis.console.core.commands import CORE_COMMANDS
from orionis.console.tasks.schedule import Schedule
from orionis.test import TestCase

class TestApplicationScheduler(TestCase):
    """Verify the project's scheduled commands resolve in the reactor."""

    async def testConfiguredTasksUseRegisteredCommands(self) -> None:
        """Validate the application task declarations against available commands.

        Returns
        -------
        None
            Assertions verify that the scheduler can describe every task.
        """
        reactor = MagicMock()
        reactor.info = AsyncMock(return_value=[
            {"signature": command.signature}
            for command in (*CORE_COMMANDS, InspireCommand)
        ])
        config = SimpleNamespace(
            store="memory",
            jitter=0,
            max_instances=1,
            misfire_grace_time=30,
            coalesce=True,
        )
        stores = SimpleNamespace(config=config)
        schedule = Schedule(reactor, MagicMock(), stores)

        Scheduler().tasks(schedule)
        tasks = await schedule.info()

        self.assertEqual([task["signature"] for task in tasks], ["app:inspire"])
        reactor.info.assert_awaited_once_with()
