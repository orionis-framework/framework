# ruff: noqa: BLE001
# Report logger and cleanup failures without replacing the original operation error.
"""Represent a background task that can be executed asynchronously."""

from __future__ import annotations
import asyncio
import functools
import inspect
from contextvars import copy_context
from typing import TYPE_CHECKING, Any
from orionis.background.contracts.task import IBackgroundTask
from orionis.failure.runtime import capture, capture_nowait, operation
from orionis.support.concurrency import close_abandoned_awaitable, complete_on_cancel
from orionis.support.facades.logger import Log

if TYPE_CHECKING:
    from collections.abc import Callable


def is_async_callable(func: object) -> bool:
    """
    Detect coroutine functions and callable instances with asynchronous calls.

    Parameters
    ----------
    func : object
        Callable to inspect. Partial objects are unwrapped first, and
        instances are inspected through their ``__call__``.

    Returns
    -------
    bool
        True for a declared asynchronous callable. Synchronous factories that
        return awaitables remain synchronous for dispatch purposes.
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
    func : collections.abc.Callable
        The function to be executed in the background.
    *args : object
        Positional arguments to pass to the function.
    **kwargs : object
        Keyword arguments to pass to the function.
    """

    __slots__ = ("__args", "__func", "__is_async", "__kwargs")
    """Declare the instance attribute slots reserved by this class."""

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
        func : collections.abc.Callable
            The function to be executed in the background.
        *args : object
            Positional arguments to pass to the function.
        **kwargs : object
            Keyword arguments to pass to the function.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.__func: Callable[..., Any] = func
        """The function to be executed in the background."""
        self.__args: tuple[object, ...] = args
        """Positional arguments to pass to the function."""
        self.__kwargs: dict[str, object] = kwargs
        """Keyword arguments to pass to the function."""
        self.__is_async: bool = is_async_callable(func)
        """Is async produced by ``is_async_callable``."""

    async def __executeSync(self) -> object:
        """Run synchronous work and release its result if the caller cancels.

        Returns
        -------
        object
            Worker result when the caller remains active.

        Raises
        ------
        asyncio.CancelledError
            After the worker has finished and an abandoned awaitable is released.
        Exception
            If the worker fails while the caller is still awaiting it.
        """
        loop = asyncio.get_running_loop()
        bound = functools.partial(self.__func, *self.__args, **self.__kwargs)
        pending = loop.run_in_executor(None, copy_context().run, bound)
        try:
            return await complete_on_cancel(pending)
        except asyncio.CancelledError:
            if not pending.cancelled() and pending.exception() is None:
                try:
                    close_abandoned_awaitable(
                        pending.result(),
                        on_error=functools.partial(
                            capture_nowait,
                            flow="background",
                            phase="cancelled_cleanup",
                        ),
                    )
                except Exception as error:
                    await capture(error, flow="background", phase="cancelled_cleanup")
            raise

    async def __call__(self) -> None:
        """
        Execute the background task, handling both sync and async functions.

        Returns
        -------
        None
            This method does not return a value.
        """
        task_name: str = getattr(
            self.__func,
            "__qualname__",
            self.__func.__class__.__name__,
        )
        with operation(flow="background", operation=task_name, isolated=True):
            try:
                if self.__is_async:
                    await self.__func(*self.__args, **self.__kwargs)  # type: ignore[arg-type]
                else:
                    result = await self.__executeSync()
                    if inspect.isawaitable(result):
                        await result
            except Exception as error:
                receipt = await capture(error, flow="background", operation=task_name)
                if receipt is None:
                    try:
                        Log.error(f"Background task '{task_name}' failed: {error}")
                    except Exception as log_error:
                        await capture(
                            log_error,
                            flow="background",
                            phase="report",
                            operation=task_name,
                        )
                raise
            else:
                try:
                    Log.info(f"Background task '{task_name}' executed successfully.")
                except Exception as error:
                    await capture(
                        error,
                        flow="background",
                        phase="report",
                        operation=task_name,
                    )
                    raise

    async def run(self) -> None:
        """
        Run the background task.

        Returns
        -------
        None
            This method does not return a value.
        """
        await self()
