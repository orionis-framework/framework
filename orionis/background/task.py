from __future__ import annotations
import asyncio
import functools
import inspect
from typing import TYPE_CHECKING, Any
from orionis.background.contracts.task import IBackgroundTask
from orionis.support.facades.logger import Log

if TYPE_CHECKING:
    from collections.abc import Callable

def is_async_callable(func: object) -> bool:
    """
    Report whether invoking a callable produces an awaitable.

    Parameters
    ----------
    func : object
        Callable to inspect. Partial objects are unwrapped first, and
        instances are inspected through their ``__call__``.

    Returns
    -------
    bool
        True when calling ``func`` returns a coroutine, False otherwise.
    """
    # Unwrap partials so pre-bound coroutine callables are still detected
    target: object = func
    while isinstance(target, functools.partial):
        target = target.func

    if inspect.iscoroutinefunction(target):
        return True

    # Callable instances expose their coroutine nature through __call__
    return callable(target) and inspect.iscoroutinefunction(target.__call__)

class BackgroundTask(IBackgroundTask):
    """
    Represent a background task that can be executed asynchronously.

    Parameters
    ----------
    func : Callable
        The function to be executed in the background.
    *args : Any
        Positional arguments to pass to the function.
    **kwargs : Any
        Keyword arguments to pass to the function.
    """

    __slots__ = ("__args", "__func", "__is_async", "__kwargs")

    def __init__(
        self,
        func: Callable,
        *args: object,
        **kwargs: object,
    ) -> None:
        """
        Initialize the BackgroundTask instance.

        Parameters
        ----------
        func : Callable
            The function to be executed in the background.
        *args : Any
            Positional arguments to pass to the function.
        **kwargs : Any
            Keyword arguments to pass to the function.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.__func: Callable[..., Any] = func
        self.__args: tuple[object, ...] = args
        self.__kwargs: dict[str, object] = kwargs
        self.__is_async: bool = is_async_callable(func)

    async def __call__(self) -> None:
        """
        Execute the background task, handling both sync and async functions.

        Returns
        -------
        None
            This method does not return a value.
        """
        task_name: str = getattr(
            self.__func, "__qualname__", self.__func.__class__.__name__,
        )
        try:
            # Await the coroutine function directly
            if self.__is_async:
                await self.__func(*self.__args, **self.__kwargs)  # type: ignore[arg-type]
            # Run the synchronous function in a thread pool executor.
            # functools.partial is required because run_in_executor only
            # accepts positional arguments and does not forward **kwargs.
            else:
                loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
                bound: functools.partial[Any] = functools.partial(
                    self.__func, *self.__args, **self.__kwargs,  # type: ignore[arg-type]
                )
                await loop.run_in_executor(None, bound)
        except Exception as error:
            Log.error(f"Background task '{task_name}' failed: {error}")
            raise
        else:
            Log.info(f"Background task '{task_name}' executed successfully.")

    async def run(self) -> None:
        """
        Run the background task.

        Returns
        -------
        None
            This method does not return a value.
        """
        await self()
