from __future__ import annotations
from typing import TYPE_CHECKING
from orionis.background.task import BackgroundTask

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

class BackgroundTasks(BackgroundTask):
    """
    Manage and execute a collection of background tasks sequentially.

    This class holds an ordered list of :class:`BackgroundTask` instances
    and runs them one after another when invoked.
    """

    __slots__ = ("tasks",)

    def __init__(self, tasks: Sequence[BackgroundTask] | None = None) -> None:
        """
        Initialize BackgroundTasks with an optional sequence of tasks.

        Parameters
        ----------
        tasks : Sequence[BackgroundTask] | None
            Optional sequence of BackgroundTask instances to initialize with.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Convert tasks to a list or initialize as empty if not provided
        self.tasks: list[BackgroundTask] = list(tasks) if tasks else []

    def addTask(
        self, func: Callable, *args: object, **kwargs: object,
    ) -> None:
        """
        Add a new BackgroundTask to the task list.

        Parameters
        ----------
        func : Callable
            The function to be executed as a background task.
        *args : object
            Positional arguments to pass to the function.
        **kwargs : object
            Keyword arguments to pass to the function.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Create and append a new BackgroundTask instance
        self.tasks.append(BackgroundTask(func, *args, **kwargs))

    async def __call__(self) -> None:
        """
        Execute all background tasks sequentially.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Await each task in the list
        for task in self.tasks:
            await task()
