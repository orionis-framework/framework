from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.console.output.executor import Executor
from orionis.database.migrations.events import MigrationEvents


class MigrationCommand(BaseCommand):
    """
    Base class shared by every migration console command.

    It centralizes the pieces all of them repeat: the ``--database``
    option selecting the target connection and the wiring that renders
    one RUNNING/DONE (or FAIL) line per migration.
    """

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = True

    # Every migration command targets an optional named connection
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags=["--database", "-d"],
            type_=str,
            required=False,
            help="Named connection to run against; defaults to the default one.",
            dest="database",
        ),
    ]

    def targetConnection(self) -> str | None:
        """
        Return the connection the command was asked to run against.

        Returns
        -------
        str or None
            Named connection, or ``None`` for the default one.
        """
        return self.getArgument("database") or None

    def progressEvents(self) -> MigrationEvents:
        """
        Build the progress callbacks rendering one line per migration.

        Returns
        -------
        MigrationEvents
            Callbacks printing RUNNING, DONE, and FAIL lines.
        """
        executor = Executor()
        return MigrationEvents(
            on_start=executor.running,
            on_success=lambda name, elapsed: executor.done(name, f"{elapsed:.2f}s"),
            on_error=lambda name, elapsed: executor.fail(name, f"{elapsed:.2f}s"),
        )

    def reportEmpty(self, message: str) -> None:
        """
        Report that the command had nothing to do.

        Parameters
        ----------
        message : str
            Message describing why nothing ran.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.info(message)
        self.newLine()
