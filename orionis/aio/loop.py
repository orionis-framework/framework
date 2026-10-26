from __future__ import annotations
import asyncio
import inspect
import sys
import threading
import types
from contextlib import contextmanager, suppress
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Generator

class Loop:
    """
    Thread-safe, platform-aware asyncio event loop manager for the Orionis Framework.

    Centralises every aspect of event loop lifecycle:

    - Optimal factory selection: uvloop (non-Windows) → ProactorEventLoop
      (Windows) → stdlib default.
    - Per-thread loop registration through asyncio as the source of truth.
    - Synchronous entry points that reject calls from a running loop.
    - Context-preserving execution of synchronous callables in worker threads.
    - Runner-managed cleanup for owned loops, without modifying borrowed loops.

    All state is class-level; no instance creation is required or intended.
    """

    # ------------------------------------------------------------------
    # Shared class state
    # ------------------------------------------------------------------

    # True when running on Windows; evaluated once at class definition.
    _IS_WIN32: ClassVar[bool] = sys.platform == "win32"

    # Cached uvloop factory; ``None`` until detection completes.
    _uvloop_factory: ClassVar[Callable[[], asyncio.AbstractEventLoop] | None] = None

    # Guard: ensures uvloop detection runs at most once across all threads.
    _uvloop_checked: ClassVar[bool] = False

    # Serialises uvloop detection to prevent duplicate work under concurrency.
    _loop_lock: ClassVar[threading.Lock] = threading.Lock()

    # Whether the optimal loop factory has been resolved yet.
    _loop_factory_resolved: ClassVar[bool] = False

    # Cached optimal loop factory; ``None`` means "use asyncio default".
    # Only valid when ``_loop_factory_resolved`` is ``True``.
    _loop_factory_cached: ClassVar[
        Callable[[], asyncio.AbstractEventLoop] | None
    ] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _getRunningLoop() -> asyncio.AbstractEventLoop | None:
        """
        Return the event loop currently running in this thread, or ``None``.

        Uses the public ``asyncio.get_running_loop()`` API with a
        ``try/except`` to avoid relying on CPython private internals.
        The overhead is negligible when a loop is present (fast path).

        Returns
        -------
        asyncio.AbstractEventLoop or None
        """
        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return None

    @staticmethod
    def _getRegisteredLoop() -> asyncio.AbstractEventLoop | None:
        """
        Return the thread's registered loop if it is still open.

        Returns
        -------
        asyncio.AbstractEventLoop or None
            The current loop, or ``None`` when absent or closed.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            return None
        return None if loop.is_closed() else loop

    # ------------------------------------------------------------------
    # Loop factory resolution
    # ------------------------------------------------------------------

    @classmethod
    def _detectUvloop(cls) -> Callable[[], asyncio.AbstractEventLoop] | None:
        """
        Detect and cache the uvloop event loop factory, if available.

        Uses double-checked locking so detection occurs at most once across
        all threads; subsequent calls return the cached result immediately.

        Returns
        -------
        Callable or None
            ``uvloop.new_event_loop`` when available on a non-Windows
            platform, otherwise ``None``.
        """
        if cls._uvloop_checked:
            return cls._uvloop_factory

        with cls._loop_lock:
            if cls._uvloop_checked:
                return cls._uvloop_factory

            if not cls._IS_WIN32:
                try:
                    import uvloop  # type: ignore[import-untyped]  # noqa: PLC0415
                    cls._uvloop_factory = uvloop.new_event_loop
                except ImportError:
                    pass

            cls._uvloop_checked = True

        return cls._uvloop_factory

    @classmethod
    def _getLoopFactory(cls) -> Callable[[], asyncio.AbstractEventLoop] | None:
        """
        Return the best available event loop factory for the current platform.

        Resolution order:

        1. uvloop (non-Windows only).
        2. ``asyncio.ProactorEventLoop`` (Windows only).
        3. ``None`` — the caller falls back to ``asyncio.new_event_loop()``.

        The result is cached after the first call; repeated invocations are
        essentially free.

        Returns
        -------
        Callable or None
        """
        if cls._loop_factory_resolved:
            return cls._loop_factory_cached

        uvloop_factory = cls._detectUvloop()
        if uvloop_factory is not None:
            cls._loop_factory_cached = uvloop_factory
            cls._loop_factory_resolved = True
            return uvloop_factory

        result: Callable[[], asyncio.AbstractEventLoop] | None = None
        if cls._IS_WIN32:
            with suppress(AttributeError):
                result = asyncio.ProactorEventLoop  # type: ignore[assignment]

        cls._loop_factory_cached = result
        cls._loop_factory_resolved = True
        return result

    @classmethod
    def _newEventLoop(cls) -> asyncio.AbstractEventLoop:
        """
        Create and register a loop using the selected platform factory.

        Returns
        -------
        asyncio.AbstractEventLoop
            A new loop registered in the calling thread.
        """
        factory = cls._getLoopFactory()
        loop = factory() if factory is not None else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

    @classmethod
    @contextmanager
    def _runnerContext(cls) -> Generator[asyncio.Runner]:
        """
        Own a Runner and restore the thread's previous loop on exit.

        Yields
        ------
        asyncio.Runner
            Runner whose loop is registered before execution begins.

        Raises
        ------
        RuntimeError
            If the owned loop is closed prematurely or left running on exit.
        """
        previous = cls._getRegisteredLoop()
        runner = asyncio.Runner(loop_factory=cls._newEventLoop)
        try:
            loop = runner.get_loop()
            try:
                yield runner
            finally:
                if loop.is_closed():
                    error_msg = "The managed event loop was closed before cleanup"
                    raise RuntimeError(error_msg)
                if loop.is_running():
                    error_msg = "The managed event loop is still running during cleanup"
                    raise RuntimeError(error_msg)
                runner.close()
        finally:
            asyncio.set_event_loop(
                previous
                if previous is not None and not previous.is_closed()
                else None,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def getEventLoop(cls) -> asyncio.AbstractEventLoop:
        """
        Return the event loop for the current thread, creating one if necessary.

        If a loop is already running in the calling thread it is returned
        immediately. Otherwise asyncio's current registered loop is returned.
        A fresh loop is created and registered when none is open; the caller
        owns that newly created loop and must close it explicitly. A subsequent
        :meth:`eventLoopContext` borrows the registered loop and will not close
        it. For automatic ownership and cleanup, enter :meth:`eventLoopContext`
        directly when no open loop is registered.

        Returns
        -------
        asyncio.AbstractEventLoop
        """
        running = cls._getRunningLoop()
        if running is not None:
            return running

        loop = cls._getRegisteredLoop()
        return loop if loop is not None else cls._newEventLoop()

    @classmethod
    def run[T](cls, coro: Coroutine[Any, Any, T]) -> T:
        """
        Execute a coroutine as the application entry point.

        Designed to be called from a context with **no** running event loop
        (e.g. CLI ``__main__``). The owned loop is registered before execution,
        fully shut down on exit, and the previous open loop is restored.
        ``KeyboardInterrupt`` and coroutine failures propagate to the caller.

        Parameters
        ----------
        coro : Coroutine
            The coroutine object to run.

        Returns
        -------
        T
            The value returned by the coroutine.

        Raises
        ------
        TypeError
            If *coro* is not a coroutine object.
        RuntimeError
            Raised when a loop is already running in the calling thread.
            Await *coro* directly instead. A rejected coroutine is left
            unconsumed; the caller must await or close it.
        KeyboardInterrupt
            If execution is interrupted by the user.
        """
        if not isinstance(coro, types.CoroutineType):
            error_msg = "A coroutine object is required"
            raise TypeError(error_msg)

        if cls._getRunningLoop() is not None:
            error_msg = (
                "Cannot run a coroutine synchronously from a running event loop; "
                "await the coroutine instead"
            )
            raise RuntimeError(error_msg)
        with cls._runnerContext() as runner:
            return runner.run(coro)

    @staticmethod
    async def execute(
        func: Callable[..., Any],
        /,
        *args: Any,  # noqa: ANN401
        **kwargs: Any,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        """
        Transparently execute a sync or async callable.

        Async callables are awaited directly; synchronous callables are
        offloaded with ``asyncio.to_thread`` to avoid blocking the loop thread
        while preserving the calling context's ``contextvars``.
        If a synchronous callable returns an awaitable, including a
        generator-based coroutine, that result is awaited on the calling loop.

        Parameters
        ----------
        func : Callable
            The function or coroutine function to invoke.
        *args : Any
            Positional arguments forwarded to *func*.
        **kwargs : Any
            Keyword arguments forwarded to *func*.

        Returns
        -------
        Any

        Raises
        ------
        TypeError
            If *func* is not callable.
        """
        if not callable(func):
            error_msg = "The provided object is not callable"
            raise TypeError(error_msg)

        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)

        result = await asyncio.to_thread(func, *args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    @classmethod
    @contextmanager
    def eventLoopContext(cls) -> Generator[asyncio.AbstractEventLoop]:
        """
        Borrow the current open loop, or create and own one for the block.

        Borrowed loops, including running loops and loops previously returned by
        :meth:`getEventLoop`, are never closed and their tasks are not cancelled.
        Nested contexts borrow the outer context's loop. Ownership remains with
        the original caller or context.

        An owned loop uses Runner cleanup: cancel and drain tasks, finalize
        asynchronous generators, shut down the default executor, close the loop,
        and clear its registration. Do not close an owned loop manually or leave
        it running on exit.

        Yields
        ------
        asyncio.AbstractEventLoop

        Raises
        ------
        RuntimeError
            If an owned loop cannot be cleaned up because it was already
            closed or is still running.
        """
        loop = cls._getRegisteredLoop()
        if loop is not None:
            yield loop
            return
        with cls._runnerContext() as runner:
            yield runner.get_loop()

    @staticmethod
    def isLoopRunning() -> bool:
        """
        Return ``True`` if an event loop is currently running in the calling thread.

        Returns
        -------
        bool
        """
        return Loop._getRunningLoop() is not None

    @staticmethod
    def createTask[T](
        coro: Coroutine[Any, Any, T],
        *,
        name: str | None = None,
    ) -> asyncio.Task[T]:
        """
        Create and schedule a new asyncio task for *coro* immediately.

        This method is synchronous. Await the returned task for its result,
        not to create the task.

        Parameters
        ----------
        coro : Coroutine
            The coroutine to schedule.
        name : str or None, optional
            An optional descriptive name for the task.

        Returns
        -------
        asyncio.Task
        """
        return asyncio.create_task(coro, name=name)

    @classmethod
    def runSync[T](cls, coro: Coroutine[Any, Any, T]) -> T:
        """
        Run a coroutine synchronously from a thread without a running loop.

        Delegates to :meth:`run` in the calling thread, preserving its context
        without a shared executor. From asynchronous code, await the coroutine
        directly; blocking the loop thread is deliberately unsupported.

        Parameters
        ----------
        coro : Coroutine

        Returns
        -------
        T
            The value returned by the coroutine.

        Raises
        ------
        TypeError
            If *coro* is not a coroutine object.
        RuntimeError
            If a loop is running in the calling thread. The coroutine remains
            unconsumed and must be awaited or closed by the caller.
        KeyboardInterrupt
            If execution is interrupted by the user.
        """
        return cls.run(coro)
