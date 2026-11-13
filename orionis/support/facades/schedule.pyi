# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from orionis.console.fluent.contracts.task import ITask
from orionis.container.contracts.facade import IFacade
from orionis.console.contracts.schedule import ISchedule

class Schedule(ISchedule, IFacade):
    @classmethod
    def command(
        cls,
        signature: str,
        args: list[str] | None = None,
        purpose: str | None = None,
    ) -> ITask:
        """Add a command for fluent configuration."""
