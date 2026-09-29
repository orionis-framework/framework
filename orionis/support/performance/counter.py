from __future__ import annotations
import time
from typing import Self, TYPE_CHECKING
from orionis.support.performance.contracts.counter import IPerformanceCounter

if TYPE_CHECKING:
    from types import TracebackType

_ERR_NOT_MEASURED: str = "Counter has not been started and stopped properly."
_ERR_NOT_STARTED: str = "Counter has not been started."
_ERR_USE_ASTOP: str = "Cannot use stop() after astart(). Use astop() instead."
_ERR_USE_STOP: str = "Cannot use astop() after start(). Use stop() instead."

class PerformanceCounter(IPerformanceCounter):
    __slots__ = (
        "_diff_time",
        "_is_async_mode",
        "_start_time",
    )

    def __init__(self) -> None:
        """
        Initialize the PerformanceCounter instance.

        Initializes internal attributes for tracking start, end, and elapsed time.

        Returns
        -------
        None
            This constructor does not return a value.
        """
        # Initialize the counter state.
        self._start_time: float | None = None
        self._diff_time: float | None = None
        self._is_async_mode: bool = False

    def start(self) -> PerformanceCounter:
        """
        Start the performance counter.

        Records the current high-resolution time as the start time.

        Returns
        -------
        PerformanceCounter
            This instance for method chaining.
        """
        # Begin a synchronous measurement.
        self._start_time = time.perf_counter()
        self._diff_time = None
        self._is_async_mode = False
        return self

    async def astart(self) -> PerformanceCounter:
        """
        Start the performance counter asynchronously.

        Records the current high-resolution time for an asynchronous measurement.

        Returns
        -------
        PerformanceCounter
            The current instance for method chaining.
        """
        # Begin an asynchronous measurement.
        self._start_time = time.perf_counter()
        self._diff_time = None
        self._is_async_mode = True
        return self

    def stop(self) -> PerformanceCounter:
        """
        Stop the performance counter and compute elapsed time.

        Records the current high-resolution time as the end time and computes the
        elapsed time since `start()` was called.

        Returns
        -------
        PerformanceCounter
            The current instance for method chaining.

        Raises
        ------
        RuntimeError
            If called after asynchronous start.
        ValueError
            If called before start.
        """
        # Ensure synchronous mode before stopping
        if self._is_async_mode:
            raise RuntimeError(_ERR_USE_ASTOP)
        start_time = self._start_time
        if start_time is None:
            raise ValueError(_ERR_NOT_STARTED)
        # Store the elapsed duration.
        self._diff_time = time.perf_counter() - start_time
        return self

    async def astop(self) -> PerformanceCounter:
        """
        Stop the performance counter asynchronously.

        Records the current high-resolution time as the end time and computes the
        elapsed time since `astart()` was called.

        Returns
        -------
        PerformanceCounter
            This instance for method chaining.

        Raises
        ------
        RuntimeError
            If called after synchronous start.
        """
        # Ensure asynchronous mode before stopping
        if not self._is_async_mode:
            raise RuntimeError(_ERR_USE_STOP)
        start_time = self._start_time
        if start_time is None:
            raise ValueError(_ERR_NOT_STARTED)
        # Store the elapsed duration.
        self._diff_time = time.perf_counter() - start_time
        return self

    def elapsedTime(self) -> float:
        """
        Return the elapsed time in seconds between the last start and stop calls.

        Raises
        ------
        ValueError
            If the counter has not been started and stopped properly.

        Returns
        -------
        float
            Elapsed time in seconds as a float.
        """
        # Ensure the counter has been started and stopped before returning elapsed time
        diff = self._diff_time
        if diff is None:
            raise ValueError(_ERR_NOT_MEASURED)
        return diff

    async def aelapsedTime(self) -> float:
        """
        Return the elapsed time in seconds asynchronously.

        Returns
        -------
        float
            Elapsed time in seconds as a float.

        Raises
        ------
        ValueError
            If the counter has not been started and stopped properly.
        """
        # Return the elapsed duration in seconds.
        diff = self._diff_time
        if diff is None:
            raise ValueError(_ERR_NOT_MEASURED)
        return diff

    def getMicroseconds(self) -> float:
        """
        Return the elapsed time in microseconds.

        Converts the elapsed time in seconds to microseconds.

        Returns
        -------
        float
            Elapsed time in microseconds.
        """
        # Return the elapsed duration in microseconds.
        diff = self._diff_time
        if diff is None:
            raise ValueError(_ERR_NOT_MEASURED)
        return diff * 1_000_000

    async def agetMicroseconds(self) -> float:
        """
        Return the elapsed time in microseconds asynchronously.

        Returns
        -------
        float
            Elapsed time in microseconds as a float.
        """
        # Return the elapsed duration in microseconds.
        diff = self._diff_time
        if diff is None:
            raise ValueError(_ERR_NOT_MEASURED)
        return diff * 1_000_000

    def getMilliseconds(self) -> float:
        """
        Return the elapsed time in milliseconds.

        Converts the elapsed time in seconds to milliseconds.

        Returns
        -------
        float
            Elapsed time in milliseconds as a float.
        """
        # Return the elapsed duration in milliseconds.
        diff = self._diff_time
        if diff is None:
            raise ValueError(_ERR_NOT_MEASURED)
        return diff * 1_000

    async def agetMilliseconds(self) -> float:
        """
        Return the elapsed time in milliseconds asynchronously.

        Returns
        -------
        float
            Elapsed time in milliseconds as a float.
        """
        # Return the elapsed duration in milliseconds.
        diff = self._diff_time
        if diff is None:
            raise ValueError(_ERR_NOT_MEASURED)
        return diff * 1_000

    def getSeconds(self) -> float:
        """
        Return the elapsed time in seconds.

        Returns
        -------
        float
            Elapsed time in seconds as a float.
        """
        # Return the elapsed duration in seconds.
        diff = self._diff_time
        if diff is None:
            raise ValueError(_ERR_NOT_MEASURED)
        return diff

    async def agetSeconds(self) -> float:
        """
        Return the elapsed time in seconds asynchronously.

        Returns
        -------
        float
            Elapsed time in seconds as a float.
        """
        # Return the elapsed duration in seconds.
        diff = self._diff_time
        if diff is None:
            raise ValueError(_ERR_NOT_MEASURED)
        return diff

    def getMinutes(self) -> float:
        """
        Return the elapsed time in minutes.

        Returns
        -------
        float
            Elapsed time in minutes as a float.
        """
        # Return the elapsed duration in minutes.
        diff = self._diff_time
        if diff is None:
            raise ValueError(_ERR_NOT_MEASURED)
        return diff / 60

    async def agetMinutes(self) -> float:
        """
        Return the elapsed time in minutes asynchronously.

        Returns
        -------
        float
            Elapsed time in minutes as a float.
        """
        # Return the elapsed duration in minutes.
        diff = self._diff_time
        if diff is None:
            raise ValueError(_ERR_NOT_MEASURED)
        return diff / 60

    def restart(self) -> PerformanceCounter:
        """
        Restart the performance counter.

        Resets internal timing attributes and starts the counter again. Useful for
        measuring a new interval without creating a new instance.

        Returns
        -------
        PerformanceCounter
            This instance for method chaining.
        """
        # Begin a new synchronous measurement.
        self._diff_time = None
        self._start_time = time.perf_counter()
        self._is_async_mode = False
        return self

    async def arestart(self) -> PerformanceCounter:
        """
        Restart the performance counter asynchronously.

        Resets internal timing attributes and starts the counter again in async
        mode.

        Returns
        -------
        PerformanceCounter
            This instance for method chaining.
        """
        # Begin a new asynchronous measurement.
        self._diff_time = None
        self._start_time = time.perf_counter()
        self._is_async_mode = True
        return self

    def __enter__(self) -> Self:
        """
        Enter the context manager and start the counter.

        Returns
        -------
        PerformanceCounter
            This instance of the performance counter.
        """
        # Start the counter when entering the context
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        Exit the context manager and stop the counter.

        Parameters
        ----------
        exc_type : type or None
            Exception type if raised, else None.
        exc_val : BaseException or None
            Exception value if raised, else None.
        exc_tb : object or None
            Traceback object if exception occurred, else None.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Stop the counter when exiting the context
        self.stop()

    async def __aenter__(self) -> Self:
        """
        Enter the async context manager and start the counter asynchronously.

        Returns
        -------
        PerformanceCounter
            This instance of the performance counter.
        """
        # Start the counter when entering the asynchronous context.
        return await self.astart()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        Exit the async context manager and stop the counter asynchronously.

        Parameters
        ----------
        exc_type : type or None
            Exception type if raised, else None.
        exc_val : BaseException or None
            Exception value if raised, else None.
        exc_tb : object or None
            Traceback object if exception occurred, else None.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Stop the counter when exiting the asynchronous context.
        await self.astop()
