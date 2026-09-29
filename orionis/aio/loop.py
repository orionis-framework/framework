from __future__ import annotations
import asyncio
import concurrent.futures
import functools
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
    - Per-thread loop creation and caching to prevent cross-thread sharing.
    - Transparent bridging between synchronous and asynchronous execution
      contexts without deadlocking a running loop.
    - Cooperative task cancellation and cleanup on context-manager exit.

    All state is class-level; no instance creation is required or intended.
    """

    # ------------------------------------------------------------------
    # Shared class state
    # ------------------------------------------------------------------

    # True when running on Windows; evaluated once at class definition.
    _IS_WIN32: ClassVar[bool] = sys.platform == "win32"

    # Per-thread event loop cache; prevents cross-thread loop sharing.
    _loop_local: ClassVar[threading.local] = threading.local()

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

    # Shared single-worker pool for sync↔async bridging; created on demand.
    _sync_executor: ClassVar[concurrent.futures.ThreadPoolExecutor | None] = None

    # Serialises lazy initialisation of ``_sync_executor``.
    _sync_executor_lock: ClassVar[threading.Lock] = threading.Lock()

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
    def _getSyncExecutor(cls) -> concurrent.futures.ThreadPoolExecutor:
        """
        Return the shared single-worker thread pool used for sync↔async bridging.

        The pool is created lazily on first access via double-checked locking
        and reused for all subsequent calls, keeping thread-creation overhead
        off hot paths.

        Returns
        -------
        concurrent.futures.ThreadPoolExecutor
        """
        if cls._sync_executor is None:
            with cls._sync_executor_lock:
                if cls._sync_executor is None:
                    cls._sync_executor = concurrent.futures.ThreadPoolExecutor(
                        max_workers=1,
                        thread_name_prefix="orionis-sync",
                    )
        return cls._sync_executor

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def getEventLoop(cls) -> asyncio.AbstractEventLoop:
        """
        Return the event loop for the current thread, creating one if necessary.

        If a loop is already running in the calling thread it is returned
        immediately.  Otherwise the per-thread cached loop is returned; a
        fresh loop is created and registered when no valid cached one exists.

        Returns
        -------
        asyncio.AbstractEventLoop
        """
        running = cls._getRunningLoop()
        if running is not None:
            return running

        loop = cls._loop_local.__dict__.get("loop")
        if loop and not loop.is_closed():
            return loop

        factory = cls._getLoopFactory()
        loop = factory() if factory else asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        cls._loop_local.loop = loop
        return loop

    @staticmethod
    def run[T](coro: Coroutine[Any, Any, T]) -> T:
        """
        Execute a coroutine as the application entry point.

        Designed to be called from a context with **no** running event loop
        (e.g. CLI ``__main__``).  Passes ``KeyboardInterrupt`` cleanly so
        the process exits with code ``0`` on ``Ctrl+C``.

        Parameters
        ----------
        coro : Coroutine
            The coroutine object to run.

        Returns
        -------
        Any
            The value returned by the coroutine, or ``0`` on
            ``KeyboardInterrupt``.

        Raises
        ------
        TypeError
            If *coro* is not a coroutine object.
        RuntimeError
            Propagated from asyncio when a loop is already running in the
            calling thread. The message belongs to the standard library and
            differs between the ``asyncio.Runner`` and ``asyncio.run``
            branches; *coro* is left unconsumed. Use :meth:`runSync` to
            bridge into a loop that is already running.
        """
        if not isinstance(coro, types.CoroutineType):
            error_msg = "A coroutine object is required"
            raise TypeError(error_msg)

        factory = Loop._getLoopFactory()
        try:
            if factory:
                with asyncio.Runner(loop_factory=factory) as runner:
                    return runner.run(coro)
            return asyncio.run(coro)
        except KeyboardInterrupt:
            return 0

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
        offloaded to the event loop's default executor to avoid blocking
        the loop thread.

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

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, functools.partial(func, *args, **kwargs),
        )
        if hasattr(result, "__await__"):
            return await result
        return result

    @staticmethod
    @contextmanager
    def eventLoopContext() -> Generator[asyncio.AbstractEventLoop]:
        """
        Context manager that provides an event loop and cleans up on exit.

        Pending tasks are cancelled cooperatively and awaited with
        ``return_exceptions=True`` so no exception escapes the ``finally``
        block.

        Yields
        ------
        asyncio.AbstractEventLoop
        """
        loop = Loop.getEventLoop()
        try:
            yield loop
        finally:
            with suppress(RuntimeError, asyncio.CancelledError):
                if not loop.is_running() and (pending := asyncio.all_tasks(loop)):
                    for task in pending:
                        task.cancel()
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True),
                    )

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
    async def createTask[T](
        coro: Coroutine[Any, Any, T],
        *,
        name: str | None = None,
    ) -> asyncio.Task[T]:
        """
        Create and schedule a new asyncio task for *coro*.

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
        return asyncio.get_running_loop().create_task(coro, name=name)

    @classmethod
    def runSync[T](cls, coro: Coroutine[Any, Any, T]) -> T:
        """
        Run a coroutine synchronously from any context.

        When no loop is running, delegates directly to :meth:`run`.
        When a loop is already running (e.g. inside an async framework),
        the coroutine is dispatched to the shared single-worker thread pool
        so it runs its own loop without deadlocking the caller.

        Parameters
        ----------
        coro : Coroutine

        Returns
        -------
        Any
        """
        if cls._getRunningLoop() is None:
            return cls.run(coro)
        return cls._getSyncExecutor().submit(cls.run, coro).result()
