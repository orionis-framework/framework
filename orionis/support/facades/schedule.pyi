# ruff: noqa: PYI021
# Keep public facade methods documented alongside their static signatures.
from collections.abc import Callable
from orionis.console.entities.task import ScheduledTaskInfo
from orionis.console.entities.scheduler_event import (
    SchedulerEvent as SchedulerEventEntity,
)
from orionis.console.contracts.schedule import ISchedule
from orionis.console.enums.events import SchedulerEvent
from orionis.console.fluent.contracts.task import ITask
from orionis.container.facades.facade import Facade

class Schedule(Facade):

    @classmethod
    def getFacadeAccessor(cls) -> type[ISchedule]:
        """Return the scheduler contract."""

    @classmethod
    async def resolve(cls, *args: object, **kwargs: object) -> ISchedule:
        """Resolve the scheduler from the container."""

    @classmethod
    def command(
        cls,
        signature: str,
        args: list[str] | None = None,
        purpose: str | None = None,
    ) -> ITask:
        """Add a command for fluent configuration."""

    @classmethod
    async def info(cls) -> list[ScheduledTaskInfo]:
        """Return information about the loaded tasks."""

    @classmethod
    async def boot(cls) -> None:
        """Boot the scheduler and register all configured tasks."""

    @classmethod
    def on(
        cls,
        event: SchedulerEvent,
        listener: Callable[[SchedulerEventEntity], object],
    ) -> ISchedule:
        """Register a listener for a scheduler event."""

    @classmethod
    def state(cls) -> str:
        """Return the current scheduler state."""

    @classmethod
    def isRunning(cls) -> bool:
        """Check whether the scheduler is running."""

    @classmethod
    def isPaused(cls) -> bool:
        """Check whether the scheduler is paused."""

    @classmethod
    def isStopped(cls) -> bool:
        """Check whether the scheduler is stopped."""

    @classmethod
    def pauseTask(cls, signature: str) -> bool:
        """Pause a task by its signature."""

    @classmethod
    def resumeTask(cls, signature: str) -> bool:
        """Resume a task by its signature."""

    @classmethod
    def removeTask(cls, signature: str) -> bool:
        """Remove a task by its signature."""

    @classmethod
    def removeAllTasks(cls) -> bool:
        """Remove all tasks from the scheduler."""

    @classmethod
    def pause(cls) -> bool:
        """Pause the scheduler."""

    @classmethod
    def resume(cls) -> bool:
        """Resume the scheduler."""

    @classmethod
    def shutdown(cls, wait: int | None = None) -> None:
        """Shut down the task scheduler."""

    @classmethod
    async def wait(cls) -> None:
        """Wait for the scheduler to stop."""
