from typing import TYPE_CHECKING
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from orionis.console.base.command import BaseCommand
from orionis.console.contracts.schedule import ISchedule
from orionis.foundation.contracts.application import IApplication

if TYPE_CHECKING:
    from orionis.console.base.contracts.scheduler import IBaseScheduler

# Maximum number of characters displayed for the purpose field before truncation
_MAX_PURPOSE_LEN: int = 30

class ScheduleListCommand(BaseCommand):

    # ruff: noqa: TC001, TC002 (DI)

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = False

    # Command signature and description
    signature: str = "schedule:list"

    # Command description
    description: str = "Lists all scheduled jobs defined in the application."

    async def handle(
        self,
        app: IApplication,
        console: Console,
    ) -> None:
        """
        Display a formatted table of scheduled jobs.

        Retrieve scheduled tasks from the ISchedule service, register them, and
        print their details in a table using the rich library.

        Parameters
        ----------
        app : IApplication
            Application instance for configuration and service resolution.
        console : Console
            Rich Console instance for output.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Retrieve the Scheduler instance from the application
        scheduler: IBaseScheduler = await app.getScheduler()

        # Create an instance of the ISchedule service
        schedule_service: ISchedule = await app.make(ISchedule)

        # Register scheduled tasks using the Scheduler's tasks method
        await app.call(scheduler, "tasks", schedule=schedule_service)

        # Retrieve the list of scheduled jobs/events
        list_tasks: list[dict] = await schedule_service.info()

        # Display a message if no scheduled jobs are found
        if not list_tasks:
            console.line()
            console.print(Panel("No scheduled jobs found.", border_style="green"))
            console.line()
            return

        # Create and configure a table to display scheduled jobs
        table = Table(show_lines=False, box=box.SIMPLE_HEAVY)
        table.add_column("Signature", style="bold cyan", no_wrap=True)
        table.add_column("Arguments", style="bold magenta")
        table.add_column("Purpose", style="bold green")
        table.add_column("Random Delay\n(Calculated Result)", style="bold yellow")
        table.add_column("Coalesce", style="bold blue")
        table.add_column("Max Instances", style="bold red")
        table.add_column("Misfire Grace Time", style="bold orange3")
        table.add_column("Start Date", style="bold bright_white")
        table.add_column("End Date", style="bold bright_white")
        table.add_column("Details", style="italic dim")

        # Populate the table with job details
        for job in list_tasks:

            # Cache the bound method to avoid repeated attribute resolution per field
            _get = job.get

            # Normalize the purpose field and truncate if it exceeds the display limit
            purpose_raw = _get("purpose")
            purpose = purpose_raw if isinstance(purpose_raw, str) else ""
            if len(purpose) > _MAX_PURPOSE_LEN:
                purpose = purpose[:_MAX_PURPOSE_LEN].rstrip() + "..."

            # Add a row with all job fields to the table
            table.add_row(
                str(_get("signature")),
                str(_get("args", [])),
                purpose,
                str(_get("random_delay")),
                str(_get("coalesce")),
                str(_get("max_instances")),
                str(_get("misfire_grace_time")),
                str(_get("start_date")),
                str(_get("end_date")),
                str(_get("details")),
            )

        # Print the table inside a panel with custom title and style
        panel = Panel(
            table,
            title="[bold green]Orionis Schedule Jobs[/]",
            expand=False,
            border_style="bright_blue",
            padding=(0, 0),
        )
        console.line()

        # Output the panel containing the jobs table
        console.print(panel)
        console.line()
