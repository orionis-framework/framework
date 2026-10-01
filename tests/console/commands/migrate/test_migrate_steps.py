from unittest.mock import AsyncMock, Mock, patch
from orionis.console.commands.migrate.refresh import MigrateRefreshCommand
from orionis.console.commands.migrate.rollback import MigrateRollbackCommand
from orionis.database.migrations.migrator import Migrator
from orionis.test import TestCase

class TestMigrationStepCommands(TestCase):
    """Verify migration step arguments reach the migrator unchanged."""

    async def testExplicitAndOmittedStepsReachTheMigrator(self) -> None:
        """Preserve zero and negative values for migrator validation.

        Returns
        -------
        None
            Commands pass explicit values through and apply omitted defaults.
        """
        cases = (
            (
                MigrateRefreshCommand,
                "refresh",
                (({}, None), ({"step": 0}, 0), ({"step": -2}, -2)),
            ),
            (
                MigrateRollbackCommand,
                "rollback",
                (({}, 1), ({"step": 0}, 0), ({"step": -2}, -2)),
            ),
        )
        for command_type, method_name, steps in cases:
            for arguments, expected in steps:
                with self.subTest(command=command_type.__name__, step=expected):
                    command = command_type()
                    command.setArguments(arguments)
                    migrator = Mock()
                    operation = AsyncMock(return_value=["migration"])
                    setattr(migrator, method_name, operation)

                    with patch.object(command, "newLine"):
                        await command.handle(migrator)

                    self.assertEqual(operation.await_args.args[0], expected)

    async def testNonpositiveStepsRaiseTheMigratorValidationError(self) -> None:
        """Propagate the migrator's positive step requirement.

        Returns
        -------
        None
            Both commands reject explicit zero and negative step values.
        """
        migrator = object.__new__(Migrator)
        for command_type in (MigrateRefreshCommand, MigrateRollbackCommand):
            for step in (0, -2):
                with self.subTest(command=command_type.__name__, step=step):
                    command = command_type()
                    command.setArguments({"step": step})
                    with (
                        patch.object(command, "newLine"),
                        self.assertRaisesRegex(ValueError, "positive integer"),
                    ):
                        await command.handle(migrator)
