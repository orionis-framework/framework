import asyncio
import os
from redis.exceptions import RedisError
from rich.console import Console  # noqa: TC002
from rich.panel import Panel
from rich.text import Text
from sqlalchemy.exc import SQLAlchemyError
from orionis.console.base.command import BaseCommand
from orionis.console.contracts.schedule import ISchedule
from orionis.console.enums.events import SchedulerEvent
from orionis.database.exceptions import DatabaseException
from orionis.foundation.contracts.application import IApplication
from orionis.support.facades.datetime import DateTime

# Ordered pairs of scheduler method names and their corresponding events,
# used to register optional event listeners defined on the Scheduler class
_LISTENER_MAP: tuple[tuple[str, SchedulerEvent], ...] = (
    ("onStarted", SchedulerEvent.STARTED),
    ("onPaused", SchedulerEvent.PAUSED),
    ("onResumed", SchedulerEvent.RESUMED),
    ("onShutdown", SchedulerEvent.SHUTDOWN),
)

class ScheduleWorkCommand(BaseCommand):
    """Register and run the application's scheduled tasks."""

    # ruff: noqa: TC001

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = False

    # Command signature and description
    signature: str = "schedule:work"

    # Command description
    description: str = "Run the scheduled tasks defined by the application."

    def __startPanel(self, console: Console) -> None:
        """
        Display a formatted scheduler start message on the console.

        Parameters
        ----------
        console : Console
            Rich console used to display the startup message.

        Returns
        -------
        None
            The startup information is printed to the console.
        """
        tz: str = DateTime.getTimezone()
        pid: int = os.getpid()
        loop = asyncio.get_running_loop()
        loop_name = loop.__class__.__name__
        now: str = DateTime.now().format("YYYY-MM-DD HH:mm:ss")

        # Print a start message for the scheduler worker using rich console.
        console.line()
        panel_content = Text.assemble(
            ("🚀 Orionis Scheduler ", "bold white on green"),
            ("\n\n", ""),
            ("✅ The scheduled tasks have started successfully.\n", "white"),
            (f"🕒 Started at: {now} | 🌐 Timezone: {tz} | 🆔 PID: {pid}\n", "dim"),
            ("⚡ Event loop: ", "cyan"),
            (f"{loop_name}\n\n", "bold magenta"),
            ("🛑 To stop, press ", "white"),
            ("Ctrl+C", "bold yellow"),
        )

        # Print the message in a styled panel.
        console.print(
            Panel(
                panel_content,
                border_style="green",
                padding=(1, 2),
            ),
        )

        # Print a separating line.
        console.line()

    async def __shutdownSchedule(self, schedule_service: ISchedule) -> None:
        """
        Request graceful shutdown and wait until it completes.

        Parameters
        ----------
        schedule_service : ISchedule
            Scheduler service to shut down.

        Returns
        -------
        None
            The scheduler service has completed its shutdown sequence.
        """
        schedule_service.shutdown()
        await schedule_service.wait()

    def __registerListeners(
        self,
        scheduler: object,
        schedule_service: ISchedule,
    ) -> None:
        """
        Register the application's available scheduler event callbacks.

        Parameters
        ----------
        scheduler : object
            Application scheduler that may define event callbacks.
        schedule_service : ISchedule
            Schedule service receiving the callbacks.

        Returns
        -------
        None
            The callbacks are registered on the schedule service.
        """
        for method_name, event in _LISTENER_MAP:
            listener = getattr(scheduler, method_name, None)
            if callable(listener):
                schedule_service.on(event, listener)

    async def handle(
        self,
        app: IApplication,
        console: Console,
    ) -> int | None:
        """
        Run the application's scheduled tasks worker.

        Parameters
        ----------
        app : IApplication
            Application instance for configuration and service resolution.
        console : Console
            Rich console used to display scheduler startup information.

        Returns
        -------
        int | None
            One when the configured backend is unavailable, otherwise None.
        """
        scheduler = await app.getScheduler()

        if not callable(getattr(scheduler, "tasks", None)):
            error_msg = (
                "Scheduler must define a callable 'tasks(schedule: ISchedule)' "
                "method."
            )
            raise TypeError(error_msg)

        schedule_service: ISchedule = await app.make(ISchedule)

        await app.call(scheduler, "tasks", schedule=schedule_service)

        self.__registerListeners(scheduler, schedule_service)

        started = False
        try:
            await schedule_service.boot()
            started = True
            if app.isDebug():
                self.__startPanel(console)
            await schedule_service.wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            if started:
                await self.__shutdownSchedule(schedule_service)
        except (DatabaseException, OSError, RedisError, SQLAlchemyError) as error:
            if started:
                await self.__shutdownSchedule(schedule_service)
            console.print(Text(f"Scheduler backend error: {error}", style="red"))
            return 1
        except Exception:
            if started:
                await self.__shutdownSchedule(schedule_service)
            raise
