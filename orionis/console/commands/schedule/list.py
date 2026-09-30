from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from orionis.console.base.command import BaseCommand
from orionis.console.contracts.schedule import ISchedule
from orionis.foundation.contracts.application import IApplication

class ScheduleListCommand(BaseCommand):
    """Display the application's registered scheduled tasks."""

    # ruff: noqa: TC001, TC002 (DI)

    # Indicates whether timestamps will be shown in the command output
    timestamps: bool = False

    # Command signature and description
    signature: str = "schedule:list"

    # Command description
    description: str = "Lists all scheduled jobs defined in the application."

    def __formatValue(self, value: object) -> str:
        """
        Format one schedule value for display in the task table.

        Parameters
        ----------
        value : object
            Value returned by the schedule information service.

        Returns
        -------
        str
            String representation of the value or a dash when it is missing.
        """
        return "-" if value is None else str(value)

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
        scheduler = await app.getScheduler()

        # Create an instance of the ISchedule service
        schedule_service: ISchedule = await app.make(ISchedule)

        # Register scheduled tasks using the Scheduler's tasks method
        await app.call(scheduler, "tasks", schedule=schedule_service)

        # Retrieve the list of scheduled jobs/events
        tasks: list[dict[str, object]] = await schedule_service.info()

        # Display a message if no scheduled jobs are found
        if not tasks:
            console.line()
            console.print(Panel("No scheduled tasks found.", border_style="green"))
            console.line()
            return

        # Create and configure a table to display scheduled jobs
        table = Table(show_lines=False, box=box.SIMPLE_HEAVY)
        table.add_column("Signature", style="bold cyan", no_wrap=True)
        table.add_column("Arguments", style="bold magenta")
        table.add_column("Keyword Arguments", style="bold magenta")
        table.add_column("Purpose", style="bold green")
        table.add_column("Random Delay", style="bold yellow")
        table.add_column("Coalesce", style="bold blue")
        table.add_column("Max Instances", style="bold red")
        table.add_column("Misfire Grace Time", style="bold orange3")
        table.add_column("Start Date", style="bold bright_white")
        table.add_column("End Date", style="bold bright_white")
        table.add_column("Details", style="italic dim")

        # Populate the table with job details
        for task in tasks:
            table.add_row(
                self.__formatValue(task.get("signature")),
                self.__formatValue(task.get("args", [])),
                self.__formatValue(task.get("kwargs", {})),
                self.__formatValue(task.get("purpose")),
                self.__formatValue(task.get("random_delay")),
                self.__formatValue(task.get("coalesce")),
                self.__formatValue(task.get("max_instances")),
                self.__formatValue(task.get("misfire_grace_time")),
                self.__formatValue(task.get("start_date")),
                self.__formatValue(task.get("end_date")),
                self.__formatValue(task.get("details")),
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
